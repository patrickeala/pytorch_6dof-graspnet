import torch
from . import networks
from os.path import join
import utils.utils as utils


class GraspNetModel:
    """ Class for training Model weights

    :args opt: structure containing configuration params
    e.g.,
    --dataset_mode -> sampling / evaluation)
    """
    def __init__(self, opt):
        self.opt = opt
        self.gpu_ids = opt.gpu_ids
        self.is_train = opt.is_train
        self.device = torch.device('cuda:{}'.format(
            self.gpu_ids[0])) if self.gpu_ids else torch.device('cpu')
        self.save_dir = join(opt.checkpoints_dir, opt.name)
        self.optimizer = None
        self.loss = None
        self.pcs = None
        self.grasps = None
        # load/define networks
        self.net = networks.define_classifier(opt, self.gpu_ids, opt.arch,
                                              opt.init_type, opt.init_gain)

        self.criterion = networks.define_loss(opt)

        self.confidence_loss = None
        if self.opt.arch == "vae":
            self.kl_loss = None
            self.reconstruction_loss = None
        elif self.opt.arch == "gan":
            self.reconstruction_loss = None
        else:
            self.classification_loss = None

        if self.is_train:
            self.optimizer = torch.optim.Adam(self.net.parameters(),
                                              lr=opt.lr,
                                              betas=(opt.beta1, 0.999))
            self.scheduler = networks.get_scheduler(self.optimizer, opt)
            utils.print_network(self.net)
        if not self.is_train or opt.continue_train:
            self.load_network(opt.which_epoch)

    def set_input(self, data):
        input_pcs = torch.from_numpy(data['pc']).float()
        input_grasps = torch.from_numpy(data['grasp_rt']).float()
        target_grasps = torch.from_numpy(data['target_cps']).float()
        # set inputs
        self.pcs = input_pcs.to(self.device).requires_grad_(self.is_train)
        self.grasps = input_grasps.to(self.device).requires_grad_(
            self.is_train)
        self.target = target_grasps.to(self.device)

    def forward(self):
        out = self.net(self.pcs, self.grasps)
        return out

    def backward(self, out):
        if self.opt.arch == 'vae':
            predicted_cp = utils.transform_control_points(
                out[0], out[0].shape[0])
            self.reconstruction_loss, self.confidence_loss = self.criterion[1](
                predicted_cp,
                self.target,
                confidence=out[1],
                confidence_weight=self.opt.confidence_weight)
            self.kl_loss = self.opt.kl_loss_weight * self.criterion[0](out[1],
                                                                       out[2])
            self.loss = self.kl_loss + self.reconstruction_loss + self.confidence_loss
        elif self.opt.arch == 'gan':
            predicted_cp = utils.transform_control_points(out[0], out.shape[0])
            self.reconstruction_loss, self.confidence_loss = self.criterion(
                predicted_cp,
                self.target,
                confidence=out[1],
                confidence_weight=self.opt.confidence_weight)
            self.loss = self.reconstruction_loss + self.confidence_loss
        elif self.opt.arch == 'evaluator':
            self.classification_loss, self.confidence_loss = self.criterion(
                out[0], self.target, out[1], self.opt.confidence_weight)
            self.loss = self.classification_loss + self.confidence_loss

        self.loss.backward()

    def optimize_parameters(self):
        self.optimizer.zero_grad()
        out = self.forward()
        self.backward(out)
        self.optimizer.step()


##################

    def load_network(self, which_epoch):
        """load model from disk"""
        save_filename = '%s_net.pth' % which_epoch
        load_path = join(self.save_dir, save_filename)
        net = self.net
        if isinstance(net, torch.nn.DataParallel):
            net = net.module
        print('loading the model from %s' % load_path)
        # PyTorch newer than 0.4 (e.g., built from
        # GitHub source), you can remove str() on self.device
        state_dict = torch.load(load_path, map_location=str(self.device))
        if hasattr(state_dict, '_metadata'):
            del state_dict._metadata
        net.load_state_dict(state_dict)

    def save_network(self, which_epoch):
        """save model to disk"""
        save_filename = '%s_net.pth' % (which_epoch)
        save_path = join(self.save_dir, save_filename)
        if len(self.gpu_ids) > 0 and torch.cuda.is_available():
            torch.save(self.net.module.cpu().state_dict(), save_path)
            self.net.cuda(self.gpu_ids[0])
        else:
            torch.save(self.net.cpu().state_dict(), save_path)

    def update_learning_rate(self):
        """update learning rate (called once every epoch)"""
        self.scheduler.step()
        lr = self.optimizer.param_groups[0]['lr']
        print('learning rate = %.7f' % lr)