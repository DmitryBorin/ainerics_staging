import argparse
import cv2
import sys
import numpy
import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject, GLib

def get_args():
    parser = argparse.ArgumentParser('')
    parser.add_argument("--cam_id", type=str, help='list id number')
    args = parser.parse_args()
    return args

def pipe_set(cam_id):
    loop = GObject.MainLoop()
    
    GObject.threads_init()
    Gst.init(None)
    Gst.segtrap_set_enabled(False)
    pipe = Gst.parse_launch("""
            rtmpsrc location=rtmp://127.0.0.1:5935/live/""" + str(cam_id) + """ ! queue !

            flvdemux name=demuxer
            demuxer.video ! queue ! decodebin ! tee name=t

            t. ! queue ! videoconvert ! video/x-raw,format=BGR ! appsink name=sink

        """)
    return pipe

#global image_arr
image_arr = None

def gst_to_opencv(sample):
    buf = sample.get_buffer()
    caps = sample.get_caps()
    arr = numpy.ndarray((caps.get_structure(0).get_value('height'),
                         caps.get_structure(0).get_value('width'),
                         3),
                        buffer=buf.extract_dup(0, buf.get_size()),
                        dtype=numpy.uint8)
    return arr

def new_buffer(sink, data):
    global image_arr
    sample = sink.emit("pull-sample")
    image_arr = gst_to_opencv(sample)
    return Gst.FlowReturn.OK

def test_connect(pipe):
    
    bus = pipe.get_bus()

    sink = Gst.Bin.get_by_name(pipe, 'sink')
    sink.set_property("emit-signals", True)
    sink.connect("new-sample", new_buffer, sink)


    ret = pipe.set_state(Gst.State.PLAYING)
    if ret == Gst.StateChangeReturn.FAILURE:
        print("Unable to set the pipeline to the playing state.")
        exit(-1)
    T = 0
    while True:
        message = bus.timed_pop_filtered(100 * Gst.MSECOND, Gst.MessageType.STATE_CHANGED | Gst.MessageType.ERROR | Gst.MessageType.EOS)
        if image_arr is not None:
            img = image_arr
            gray = cv2.cvtColor(img,cv2.COLOR_BGR2GRAY)
            cv2.imwrite("result.png", gray)
            print("Screen has been saved")
            return True
        else:
            #print("No image_arr")
            T += 1

        if message:
            if message.type == Gst.MessageType.ERROR:
                err, debug = message.parse_error()
                print("Error received from element %s: %s" % (
                    message.src.get_name(), err))
                print("Debugging information: %s" % debug)
                break
            elif message.type == Gst.MessageType.EOS:
                print("End-Of-Stream reached.")
                break
            elif message.type == Gst.MessageType.STATE_CHANGED:
                if isinstance(message.src, Gst.Pipeline):
                    old_state, new_state, pending_state = message.parse_state_changed()
                        #print("Pipeline state changed from %s to %s." %
                        #   (old_state.value_nick, new_state.value_nick))
            else:
                print message.type
                # print("Unexpected message received.")
        if (T>80): return False

if __name__ == '__main__':
    args = get_args()
    
    pipe = pipe_set(args.cam_id)
    status = test_connect(pipe)
    print(str(args.cam_id) + ': ', status)
