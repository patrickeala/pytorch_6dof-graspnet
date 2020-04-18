import torch


def control_point_l1_loss_better_than_threshold(pred_control_points,
                                                gt_control_points, confidence,
                                                confidence_threshold):
    npoints = pred_control_points.shape[1]
    mask = torch.greater_equal(confidence, confidence_threshold)
    mask_ratio = torch.mean(mask)
    mask = torch.repeat_interleave(mask, npoints, dim=1)
    p1 = pred_control_points[mask]
    p2 = gt_control_points[mask]

    return control_point_l1_loss(p1, p2), mask_ratio


def accuracy_better_than_threshold(pred_success_logits, gt, confidence,
                                   confidence_threshold):
    """
      Computes average precision for the grasps with confidence > threshold.
    """
    pred_classes = torch.argmax(pred_success_logits, -1)
    correct = torch.equal(pred_classes, gt)
    mask = torch.squeeze(torch.greater_equal(confidence, confidence_threshold),
                         -1)

    positive_acc = torch.sum(correct * mask * gt) / torch.max(
        torch.sum(mask * gt), torch.tensor(1))
    negative_acc = torch.sum(correct * mask * (1. - gt)) / torch.max(
        torch.sum(mask * (1. - gt)), torch.tensor(1))

    return 0.5 * (positive_acc + negative_acc), torch.sum(mask) / gt.shape[0]


def control_point_l1_loss(pred_control_points,
                          gt_control_points,
                          confidence=None,
                          confidence_weight=None):
    """
      Computes the l1 loss between the predicted control points and the
      groundtruth contorl points on the gripper.
    """
    confidence_term = torch.tensor(0, dtype=torch.float32)
    print('control_point_l1_loss', pred_control_points.shape,
          gt_control_points.shape)
    error = torch.sum(torch.abs(pred_control_points - gt_control_points), -1)
    error = torch.mean(error, -1)
    if confidence is not None:
        assert (confidence_weight is not None)
        error *= confidence
        confidence_term = torch.mean(
            torch.log(torch.max(confidence,
                                torch.tensor(1e-10)))) * confidence_weight
        print('confidence_term = ', confidence_term.shape)

    print('l1_error = {}'.format(error.shape))
    if confidence is None:
        return torch.mean(error)
    else:
        return torch.mean(error), -confidence_term


def classification_with_confidence_loss(pred_logit, gt, confidence,
                                        confidence_weight):
    """
      Computes the cross entropy loss and confidence term that penalizes
      outputing zero confidence. Returns cross entropy loss and the confidence
      regularization term.
    """
    logp = torch.nn.functional.log_softmax(pred_logit)
    logpy = torch.gather(logp, 1, torch.tensor(gt))
    classification_loss = -(logpy).mean()
    confidence_term = torch.mean(
        torch.log(torch.max(confidence, torch.tensor(1e-10))))

    return classification_loss, -confidence_term


def min_distance_loss(
        pred_control_points,
        gt_control_points,
        confidence=None,
        confidence_weight=None,
        threshold=None,
):
    """
    Computes the minimum distance (L1 distance)between each gt control point 
    and any of the predicted control points.

    Args: 
      pred_control_points: tensor of (N_pred, M, 4) shape. N is the number of
        grasps. M is the number of points on the gripper.
      gt_control_points: (N_gt, M, 4)
      confidence: tensor of N_pred, tensor for the confidence of each 
        prediction.
      confidence_weight: float, the weight for confidence loss.
    """
    pred_shape = pred_control_points.shape
    gt_shape = gt_control_points.shape

    if len(pred_shape) != 3:
        raise ValueError(
            "pred_control_point should have len of 3. {}".format(pred_shape))
    if len(gt_shape) != 3:
        raise ValueError(
            "gt_control_point should have len of 3. {}".format(gt_shape))
    if np.any([
            p != gt for i, (p, gt) in enumerate(zip(pred_shape, gt_shape))
            if i > 0
    ]):
        raise ValueError("shapes do no match {} != {}".format(
            pred_shape, gt_shape))

    # N_pred x Ngt x M x 3
    error = torch.expand_dims(pred_control_points, 1) - torch.expand_dims(
        gt_control_points, 0)
    error = torch.sum(torch.abs(error),
                      -1)  # L1 distance of error (N_pred, N_gt, M)
    error = torch.mean(
        error, -1)  # average L1 for all the control points. (N_pred, N_gt)
    min_distance_error = torch.min(
        error, 0)  # take the min distance for each gt control point. (N_gt)
    #print('min_distance_error', get_shape(min_distance_error))
    if confidence is not None:
        closest_index = torch.argmin(error, 0)  # (N_gt)
        #print('closest_index', get_shape(closest_index))
        selected_confidence = torch.nn.functional.one_hot(
            closest_index)  # (N_gt, N_pred)
        #print('selected_confidence', selected_confidence)
        selected_confidence *= torch.expand_dims(confidence, 0)
        #print('selected_confidence', selected_confidence)
        selected_confidence = torch.sum(selected_confidence, -1)  # N_gt
        #print('selected_confidence', selected_confidence)
        min_distance_error *= selected_confidence
        confidence_term = torch.mean(
            torch.log(torch.max(confidence,
                                torch.tensor(1e-4)))) * confidence_weight
    else:
        confidence_term = 0.

    return torch.mean(min_distance_error), -confidence_term


def min_distance_better_than_threshold(pred_control_points, gt_control_points,
                                       confidence, confidence_threshold):
    error = torch.expand_dims(pred_control_points, 1) - torch.expand_dims(
        gt_control_points, 0)
    error = torch.sum(torch.abs(error),
                      -1)  # L1 distance of error (N_pred, N_gt, M)
    error = torch.mean(
        error, -1)  # average L1 for all the control points. (N_pred, N_gt)
    error = torch.min(error, -1)  # (B, N_pred)
    mask = torch.greater_equal(confidence, confidence_threshold)
    mask = torch.squeeze(mask, dim=-1)

    return torch.mean(error[mask]), torch.mean(mask)


def kl_divergence(mu, log_sigma):
    """
      Computes the kl divergence for batch of mu and log_sigma.
    """
    return torch.mean(
        -.5 * torch.sum(1. + log_sigma - mu**2 - torch.exp(log_sigma), dim=-1))