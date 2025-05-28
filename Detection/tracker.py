#from sort import Sort #Detection에서 테스트할 때
from Detection.sort import Sort #main/app.py로 테스트할 때

import numpy as np

def init_tracker():
    
    return Sort(iou_threshold=0.05)

def update_tracks(tracker, detections):

    if detections:
        dets_np = np.array(detections)
    
    else:
        dets_np = np.empty((0, 5))
    
    return tracker.update(dets_np)