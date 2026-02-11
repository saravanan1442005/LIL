# tracker.py
from deep_sort_realtime.deepsort_tracker import DeepSort

class EcoTracker:
    def __init__(self):
        # max_age: how many frames to 'remember' an object if it's hidden
        self.tracker = DeepSort(max_age=30, n_init=3)

    def update(self, detections, frame):
        # Matches new detections with existing IDs
        return self.tracker.update_tracks(detections, frame=frame)