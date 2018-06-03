import argparse
import os
import sys
import time
import tensorflow as tf
import numpy as np
import cv2
from scipy import misc

from model import DeepLab_Fast, FlowNets, Decision
from tools.img_utils import decode_labels
from tools.flow_utils import warp
from tools.image_reader import inputs
from tools.overlap import overlap4

DATA_DIRECTORY = '/home/rohana/.kaggle/competitions/cvpr-2018-autonomous-driving/test/' # '/home/rohana/project/cityscapes/leftImg8bit/demoVideo/stuttgart_00/'
DATA_LIST_PATH = 'tools/road01_cam_5_video_1_image_list_testimg_list.txt' # '/home/rohana/project/cityscapes/leftImg8bit/demoVideo/stuttgart_00_list.txt'  #
RESTORE_FROM = './checkpoint/'
SAVE_DIR = './video/'
NUM_CLASSES = 19
NUM_STEPS = 136  # Number of images in the video.
OVERLAP = 64  # power of 8
TARGET = 90.0
input_size = [2560, 3328] # <-- WAD image size
IMG_MEAN = np.array((104.00698793, 116.66876762, 122.67891434), dtype=np.float32)


def get_arguments():
    """Parse all the arguments provided from the CLI.
    
    Returns:
      A list of parsed arguments.
    """
    parser = argparse.ArgumentParser(description="Dynamic Video Segmentation Network")
    parser.add_argument("--data_dir", type=str, default=DATA_DIRECTORY,
                        help="Path to the directory containing the dataset.")
    parser.add_argument("--data_list", type=str, default=DATA_LIST_PATH,
                        help="Path to the file listing the images in the dataset.")
    parser.add_argument("--restore_from", type=str, default=RESTORE_FROM,
                        help="Where restore model parameters from.")
    parser.add_argument("--decision_from", type=str, default=RESTORE_FROM,
                        help="Where restore decision model parameters from.")
    parser.add_argument("--save_dir", type=str, default=SAVE_DIR,
                        help="Where to save segmented output.")
    parser.add_argument("--num_steps", type=int, default=NUM_STEPS,
                        help="Number of images in the video.")
    parser.add_argument("--overlap", type=int, default=OVERLAP,
                        help="Overlapping size.")
    parser.add_argument("--target", type=float, default=TARGET,
                        help="Confidence score threshold.")
    parser.add_argument("--dynamic", action="store_true",
                        help="Whether to dynamically adjust target")
    return parser.parse_args()


def load(saver, sess, ckpt_path):
    """Load trained weights.

    Args:
      saver: TensorFlow saver object.
      sess: TensorFlow session.
      ckpt_path: path to checkpoint file with parameters.
    """
    saver.restore(sess, ckpt_path)
    print("Restored model parameters from {}".format(ckpt_path))


def main():
    """Create the model and start the evaluation process."""
    args = get_arguments()
    print(args)

    tf.reset_default_graph()
    
    # Input size
    height = input_size[0]//2
    height_overlap = height+args.overlap
    width = input_size[1]//2
    width_overlap = width+args.overlap
    
    # Input.
    image_s, image_f = inputs(args.data_dir, args.data_list, 1, input_size, args.overlap)
    image_s = tf.squeeze(image_s)
    image_f = tf.squeeze(image_f)

    # Set placeholder 
    image_in = tf.placeholder(tf.float32, [height_overlap, width_overlap, 3])
    key_image = tf.placeholder(tf.float32, [4, height_overlap//2, width_overlap//2, 3])
    key_pred = tf.placeholder(tf.float32, [1, height_overlap//16, width_overlap//16, NUM_CLASSES])
    flow_field = tf.placeholder(tf.float32, [1, height_overlap//8, width_overlap//8, 2])
    scale_field = tf.placeholder(tf.float32, [1, height_overlap//8, width_overlap//8, NUM_CLASSES])
    output = tf.placeholder(tf.uint8, [1, input_size[0], input_size[1], 1])

    print('HEIGHT AND WIDTH')
    print(height_overlap//2, width_overlap//2)
    print(height_overlap//8, width_overlap//8)


    # Input image.
    image_batch = tf.expand_dims(image_in, 0)
    current_frame = image_f
    key_frame = key_image

    # Create network.
    net = DeepLab_Fast({'data': image_batch}, num_classes=NUM_CLASSES)
    flowNet = FlowNets(current_frame, key_frame)
    decisionNet = Decision(feature_size=[4, 8])
    restore_var = tf.global_variables()

    # Segmentation path.
    raw_pred = net.layers['fc_out']
    raw_output = tf.image.resize_bilinear(raw_pred, [height_overlap, width_overlap])
    raw_max = tf.reduce_max(raw_output, axis=3, keep_dims=True)
    raw_output = tf.cast(tf.argmax(raw_output, axis=3), tf.uint8)
    seg_pred = tf.expand_dims(raw_output, dim=3)  # Create 4-d tensor.
        
    # Estimation Flow and feature for decision network.
    flows = flowNet.inference()
    flow_feature = tf.image.resize_bilinear(flows['feature'], [4, 8])

    # Spatial warping path.
    warp_pred = warp(key_pred, flow_field)
    scale_pred = tf.multiply(warp_pred, scale_field)
    wrap_output = tf.image.resize_bilinear(scale_pred, [height_overlap, width_overlap])
    wrap_max = tf.reduce_max(wrap_output, axis=3, keep_dims=True)
    wrap_output = tf.cast(tf.argmax(wrap_output, axis=3), tf.uint8)
    flow_pred = tf.expand_dims(wrap_output, dim=3)  # Create 4-d tensor.
    
    # Segmented image
    pred_img = decode_labels(output, NUM_CLASSES)

    # Set up tf session and initialize variables.
    config = tf.ConfigProto()
    config.gpu_options.allow_growth = True
    sess = tf.Session(config=config)
    sess.run(tf.global_variables_initializer())
    sess.run(tf.local_variables_initializer())
    
    # Load weights.
    decision_var = [v for v in restore_var if 'decision' in v.name]
    model_var = [v for v in restore_var if 'warp' not in v.name and 'decision' not in v.name]

    ckpt = tf.train.get_checkpoint_state(args.restore_from)
    if ckpt and ckpt.model_checkpoint_path:
        loader = tf.train.Saver(var_list=model_var)
        load(loader, sess, ckpt.model_checkpoint_path)
    else:
        print('No checkpoint file found.')

    ckpt = tf.train.get_checkpoint_state(args.decision_from)
    if ckpt and ckpt.model_checkpoint_path:
        loader = tf.train.Saver(var_list=decision_var)
        load(loader, sess, ckpt.model_checkpoint_path)
    else:
        print('No checkpoint file found.')

    # Start queue threads.
    threads = tf.train.start_queue_runners(sess=sess)

    if not os.path.exists(args.save_dir):
        os.makedirs(args.save_dir)

    # Register
    targets = [args.target, args.target, args.target, args.target]
    key_outputs = [None, None, None, None]
    preds = np.zeros((1, input_size[0], input_size[1], 1), dtype=np.uint8)
    preds_value = np.zeros((1, input_size[0], input_size[1], 1), dtype=np.float32)
    region = 4
    seg_step = 0
    flow_step = 0

    for step in range(args.num_steps):
        start_time = time.time()
        if step == 0:
            image_inputs, key_inputs = sess.run([image_s, image_f])
            for i in range(region):
                print("Initial region {}".format(i))
                key_outputs[i], pred, max_value = sess.run([raw_pred, seg_pred, raw_max],
                                feed_dict={image_in: image_inputs[i]})
                overlap4(i, pred, max_value, preds, preds_value, input_size=[height, width], overlap=args.overlap)

        else:
            image_inputs, key_tmps, flow_features, flow_fields, scale_fields = sess.run([image_s, image_f, flow_feature,
                                                                                         flows['flow'], flows['scale']],
                                                                                        feed_dict={key_image:
                                                                                                       key_inputs})
            pred_scores = np.squeeze(decisionNet.pred(sess, flow_features))
            for i in range(region):
                print("step {} region {} predict score: {:.3}  target: {:.3}".format(step, i, pred_scores[i],
                                                                                     targets[i]))
                if pred_scores[i] < targets[i]:
                    if args.dynamic:
                        targets[i] -= 1
                    seg_step += 1
                    print("Segmentation Path")
                    key_inputs[i] = key_tmps[i]
                    key_outputs[i], pred, max_value = sess.run([raw_pred, seg_pred, raw_max],
                                                               feed_dict={image_in:image_inputs[i]})

                else:
                    if args.dynamic:
                        targets[i] += 0.1
                    flow_step += 1
                    print("Spatial Warping Path")
                    pred, max_value = sess.run([flow_pred, wrap_max],
                                               feed_dict={flow_field: np.expand_dims(flow_fields[i], 0),
                                                          scale_field: np.expand_dims(scale_fields[i], 0),
                                                          key_pred: key_outputs[i]})
                overlap4(i, pred, max_value, preds, preds_value, input_size=[height, width], overlap=args.overlap)
        
        # measure time
        total_time = time.time() - start_time
        print("fps: {:.3}".format(1/total_time))

        # Write result image
        mask = sess.run(pred_img, feed_dict={output: preds})
        misc.imsave(args.save_dir + 'mask' + str(step) + '.png', mask[0])
        print('#' * 32)
        print(type(mask))

    print('\nFinish!')
    print("segmentation steps:", seg_step, "flow steps:", flow_step)


if __name__ == '__main__':
    main()
