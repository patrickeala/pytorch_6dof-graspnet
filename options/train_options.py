from .base_options import BaseOptions


class TrainOptions(BaseOptions):
    def initialize(self):
        BaseOptions.initialize(self)
        self.parser.add_argument(
            '--print_freq',
            type=int,
            default=10,
            help='frequency of showing training results on console')
        self.parser.add_argument('--save_latest_freq',
                                 type=int,
                                 default=250,
                                 help='frequency of saving the latest results')
        self.parser.add_argument(
            '--save_epoch_freq',
            type=int,
            default=1,
            help='frequency of saving checkpoints at the end of epochs')
        self.parser.add_argument(
            '--run_test_freq',
            type=int,
            default=1,
            help='frequency of running test in training script')
        self.parser.add_argument(
            '--continue_train',
            action='store_true',
            help='continue training: load the latest model')
        self.parser.add_argument(
            '--epoch_count',
            type=int,
            default=1,
            help=
            'the starting epoch count, we save the model by <epoch_count>, <epoch_count>+<save_latest_freq>, ...'
        )
        self.parser.add_argument('--phase',
                                 type=str,
                                 default='train',
                                 help='train, val, test, etc')
        self.parser.add_argument(
            '--which_epoch',
            type=str,
            default='latest',
            help='which epoch to load? set to latest to use latest cached model'
        )
        self.parser.add_argument('--niter',
                                 type=int,
                                 default=100,
                                 help='# of iter at starting learning rate')
        self.parser.add_argument(
            '--niter_decay',
            type=int,
            default=2000,
            help='# of iter to linearly decay learning rate to zero')
        self.parser.add_argument('--beta1',
                                 type=float,
                                 default=0.9,
                                 help='momentum term of adam')
        self.parser.add_argument('--lr',
                                 type=float,
                                 default=0.0002,
                                 help='initial learning rate for adam')
        self.parser.add_argument(
            '--lr_policy',
            type=str,
            default='lambda',
            help='learning rate policy: lambda|step|plateau')
        self.parser.add_argument(
            '--lr_decay_iters',
            type=int,
            default=50,
            help='multiply by a gamma every lr_decay_iters iterations')
        self.parser.add_argument('--kl_loss_weight', type=float, default=0.01)
        self.parser.add_argument(
            '--confidence_weight',
            type=float,
            default=1.0,
            help=
            'initially I wanted to compute confidence for vae and evaluator outputs, '
            'setting the confidence weight to 1. immediately pushes the confidence to 1.0.'
        )
        self.parser.add_argument(
            '--train_evaluator',
            type=int,
            default=0,
            help='if set to 1, trains evaluator. 0: trains vae')
        self.parser.add_argument(
            '--gan',
            type=int,
            default=0,
            help='If 1 uses gan formulation to train instead of vae')
        self.is_train = True