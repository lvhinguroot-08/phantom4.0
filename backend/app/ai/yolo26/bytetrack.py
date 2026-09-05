"""
Pure-Python ByteTrack Engine for PHANTOM Surveillance
====================================================
High-accuracy multi-object tracking utilizing:
1. 2D Bounding Box Kalman Filter for motion prediction across frame drops.
2. Two-stage detection matching:
   - Stage 1: Matches confirmed tracks against high-confidence detections.
   - Stage 2: Matches remaining unassociated tracks against low-confidence detections
     to recover partially occluded or distant moving vehicles.
3. Zero native C-extension compilation dependencies:
   Utilizes standard scipy.optimize.linear_sum_assignment (100% reliable on Windows host).
"""
from collections import deque
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
from scipy.optimize import linear_sum_assignment

from .kalman_filter import KalmanFilter


class TrackState(int, Enum):
    New = 0
    Tracked = 1
    Lost = 2
    Removed = 3


class BaseTrack:
    _count = 0

    track_id = 0
    is_activated = False
    state = TrackState.New

    history: deque = deque(maxlen=50)
    features: List[Any] = []
    curr_feature: Optional[Any] = None
    score = 0.0
    start_frame = 0
    frame_id = 0
    time_since_update = 0

    # multi-camera
    location = (np.inf, np.inf)

    @property
    def end_frame(self) -> int:
        return self.frame_id

    @classmethod
    def next_id(cls) -> int:
        cls._count += 1
        return cls._count

    @classmethod
    def reset_counter(cls) -> None:
        cls._count = 0

    def mark_lost(self) -> None:
        self.state = TrackState.Lost

    def mark_removed(self) -> None:
        self.state = TrackState.Removed


class STrack(BaseTrack):
    shared_kalman = KalmanFilter()

    def __init__(
        self,
        tlbr: np.ndarray,
        score: float,
        class_name: str,
        raw_det: Optional[Dict[str, Any]] = None,
    ) -> None:
        # wait activate
        self._tlbr = np.asarray(tlbr, dtype=float)
        self.kalman_filter: Optional[KalmanFilter] = None
        self.mean: Optional[np.ndarray] = None
        self.covariance: Optional[np.ndarray] = None
        self.is_activated = False

        self.score = float(score)
        self.class_name = str(class_name)
        self.object_class = str(class_name).upper()
        self.raw_det = raw_det or {}
        self.tracklet_len = 0
        self.class_history: deque = deque(maxlen=20)
        self.class_history.append((self.object_class, self.score))

    def predict(self) -> None:
        mean_state = self.mean.copy() if self.mean is not None else None
        if mean_state is not None and self.state != TrackState.Tracked:
            mean_state[7] = 0
        if self.kalman_filter is not None and mean_state is not None and self.covariance is not None:
            self.mean, self.covariance = self.kalman_filter.predict(mean_state, self.covariance)

    @staticmethod
    def multi_predict(stracks: List["STrack"]) -> None:
        if len(stracks) > 0:
            for st in stracks:
                st.predict()

    def activate(self, kalman_filter: KalmanFilter, frame_id: int) -> None:
        """Start a new tracklet."""
        self.kalman_filter = kalman_filter
        self.track_id = self.next_id()
        self.mean, self.covariance = self.kalman_filter.initiate(self.tlbr_to_xyah(self._tlbr))

        self.tracklet_len = 0
        self.state = TrackState.Tracked
        if frame_id == 1:
            self.is_activated = True
        self.frame_id = frame_id
        self.start_frame = frame_id

    def re_activate(self, new_track: "STrack", frame_id: int, new_id: bool = False) -> None:
        if self.kalman_filter is not None and self.mean is not None and self.covariance is not None:
            self.mean, self.covariance = self.kalman_filter.update(
                self.mean, self.covariance, self.tlbr_to_xyah(new_track.tlbr)
            )
        self.tracklet_len = 0
        self.state = TrackState.Tracked
        self.is_activated = True
        self.frame_id = frame_id
        if new_id:
            self.track_id = self.next_id()
        self.score = new_track.score
        self.class_name = new_track.class_name
        self.object_class = new_track.object_class
        self.raw_det = new_track.raw_det
        self.class_history.append((self.object_class, self.score))

    def update(self, new_track: "STrack", frame_id: int) -> None:
        """
        Update a matched track.
        """
        self.frame_id = frame_id
        self.tracklet_len += 1

        new_tlbr = new_track.tlbr
        if self.kalman_filter is not None and self.mean is not None and self.covariance is not None:
            self.mean, self.covariance = self.kalman_filter.update(
                self.mean, self.covariance, self.tlbr_to_xyah(new_tlbr)
            )
        self.state = TrackState.Tracked
        self.is_activated = True

        self.score = new_track.score
        self.class_name = new_track.class_name
        self.object_class = new_track.object_class
        self.raw_det = new_track.raw_det
        self.class_history.append((self.object_class, self.score))

    @property
    def tlbr(self) -> np.ndarray:
        """Convert bounding box to format `(min x, min y, max x, max y)`."""
        if self.mean is None:
            return self._tlbr.copy()
        ret = self.mean[:4].copy()
        ret[2] *= ret[3]
        ret[:2] -= ret[2:] / 2
        ret[2:] += ret[:2]
        return ret

    @staticmethod
    def tlbr_to_xyah(tlbr: np.ndarray) -> np.ndarray:
        """Convert bounding box to format `(center x, center y, aspect ratio, height)`."""
        ret = np.asarray(tlbr).copy()
        ret[2:] -= ret[:2]
        ret[:2] += ret[2:] / 2
        ret[2] /= max(1e-5, ret[3])
        return ret

    def to_dict(self) -> Dict[str, Any]:
        """Convert track state to dictionary."""
        box = self.tlbr
        x1, y1, x2, y2 = float(box[0]), float(box[1]), float(box[2]), float(box[3])
        w = max(0.0, x2 - x1)
        h = max(0.0, y2 - y1)
        return {
            "track_id": self.track_id,
            "state": self.state.name,
            "score": round(self.score, 4),
            "object_class": self.object_class,
            "class_name": self.class_name,
            "bbox": {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "width": w, "height": h},
            "tracklet_len": self.tracklet_len,
            "frame_id": self.frame_id,
        }


def bbox_ious(atlbrs: np.ndarray, btlbrs: np.ndarray) -> np.ndarray:
    """Calculate IoU distance matrix between two lists of boxes."""
    ious = np.zeros((len(atlbrs), len(btlbrs)), dtype=float)
    if ious.size == 0:
        return ious

    atlbrs = np.ascontiguousarray(atlbrs, dtype=float)
    btlbrs = np.ascontiguousarray(btlbrs, dtype=float)

    for i, a in enumerate(atlbrs):
        a_area = max(0.0, a[2] - a[0]) * max(0.0, a[3] - a[1])
        for j, b in enumerate(btlbrs):
            b_area = max(0.0, b[2] - b[0]) * max(0.0, b[3] - b[1])
            ix1 = max(a[0], b[0])
            iy1 = max(a[1], b[1])
            ix2 = min(a[2], b[2])
            iy2 = min(a[3], b[3])
            inter = max(0.0, ix2 - ix1) * max(0.0, iy2 - iy1)
            union = a_area + b_area - inter
            if union > 0:
                ious[i, j] = inter / union
    return ious


def linear_assignment(cost_matrix: np.ndarray, thresh: float) -> Tuple[List[Tuple[int, int]], List[int], List[int]]:
    """Linear sum assignment (Hungarian algorithm) with threshold gating."""
    if cost_matrix.size == 0:
        return [], list(range(cost_matrix.shape[0])), list(range(cost_matrix.shape[1]))

    row_ind, col_ind = linear_sum_assignment(cost_matrix)
    matches: List[Tuple[int, int]] = []
    unmatched_a: List[int] = []
    unmatched_b: List[int] = []

    matched_cols = set()
    for r, c in zip(row_ind, col_ind):
        if cost_matrix[r, c] <= thresh:
            matches.append((r, c))
            matched_cols.add(c)
        else:
            unmatched_a.append(r)

    for r in range(cost_matrix.shape[0]):
        if r not in row_ind or (r in row_ind and cost_matrix[r, col_ind[list(row_ind).index(r)]] > thresh):
            if r not in unmatched_a:
                unmatched_a.append(r)

    for c in range(cost_matrix.shape[1]):
        if c not in matched_cols:
            unmatched_b.append(c)

    return matches, unmatched_a, unmatched_b


class BYTETracker:
    """
    ByteTrack: Multi-Object Tracking by Associating Every Detection Box.
    Pure-Python SciPy implementation for high stability in production environments.
    """

    def __init__(
        self,
        track_thresh: float = 0.50,
        track_buffer: int = 30,
        match_thresh: float = 0.80,
        frame_rate: int = 30,
    ) -> None:
        self.tracked_stracks: List[STrack] = []
        self.lost_stracks: List[STrack] = []
        self.removed_stracks: List[STrack] = []

        self.frame_id = 0
        self.track_thresh = track_thresh
        self.match_thresh = match_thresh
        self.buffer_size = int(frame_rate / 30.0 * track_buffer)
        self.max_time_lost = self.buffer_size
        self.kalman_filter = KalmanFilter()

    def reset(self) -> None:
        self.tracked_stracks.clear()
        self.lost_stracks.clear()
        self.removed_stracks.clear()
        self.frame_id = 0
        STrack.reset_counter()

    def update(self, detections: List[Dict[str, Any]]) -> List[STrack]:
        """
        Process frame detections through the two-stage ByteTrack association pipeline.
        """
        self.frame_id += 1
        activated_starcks: List[STrack] = []
        refind_stracks: List[STrack] = []
        lost_stracks: List[STrack] = []
        removed_stracks: List[STrack] = []

        scores: List[float] = []
        bboxes: List[List[float]] = []
        cnames: List[str] = []
        raw_dets: List[Dict[str, Any]] = []

        for d in detections:
            bx = d.get("bbox") or d.get("bounding_box") or {}
            x1 = float(bx.get("x1", 0.0))
            y1 = float(bx.get("y1", 0.0))
            x2 = float(bx.get("x2", 0.0))
            y2 = float(bx.get("y2", 0.0))
            conf = float(d.get("confidence", 0.0))
            cname = str(d.get("object_class") or d.get("class_name") or "OBJECT")

            scores.append(conf)
            bboxes.append([x1, y1, x2, y2])
            cnames.append(cname)
            raw_dets.append(d)

        # Partition detections into high and low confidence sets
        detections_high: List[STrack] = []
        detections_low: List[STrack] = []

        for i in range(len(bboxes)):
            st = STrack(np.array(bboxes[i]), scores[i], cnames[i], raw_det=raw_dets[i])
            if scores[i] >= self.track_thresh:
                detections_high.append(st)
            elif scores[i] >= 0.10:
                detections_low.append(st)

        # Unconfirmed tracks (new tracks waiting for second association)
        unconfirmed: List[STrack] = []
        tracked_stracks: List[STrack] = []
        for track in self.tracked_stracks:
            if not track.is_activated:
                unconfirmed.append(track)
            else:
                tracked_stracks.append(track)

        # Step 1: Predict current locations of existing tracks with Kalman filter
        strack_pool = self._joint_stracks(tracked_stracks, self.lost_stracks)
        STrack.multi_predict(strack_pool)

        # Step 2: First association with high score detections
        dists = self._iou_distance(strack_pool, detections_high)
        matches, u_track, u_detection = linear_assignment(dists, thresh=self.match_thresh)

        for itracked, idet in matches:
            track = strack_pool[itracked]
            det = detections_high[idet]
            if track.state == TrackState.Tracked:
                track.update(det, self.frame_id)
                activated_starcks.append(track)
            else:
                track.re_activate(det, self.frame_id, new_id=False)
                refind_stracks.append(track)

        # Step 3: Second association with low score detections (bridges occlusions)
        r_tracked_stracks = [strack_pool[i] for i in u_track if strack_pool[i].state == TrackState.Tracked]
        dists = self._iou_distance(r_tracked_stracks, detections_low)
        matches, u_r_track, _ = linear_assignment(dists, thresh=0.5)

        for itracked, idet in matches:
            track = r_tracked_stracks[itracked]
            det = detections_low[idet]
            if track.state == TrackState.Tracked:
                track.update(det, self.frame_id)
                activated_starcks.append(track)
            else:
                track.re_activate(det, self.frame_id, new_id=False)
                refind_stracks.append(track)

        # Tracks that remain unmatched after second association are marked lost
        for it in u_r_track:
            track = r_tracked_stracks[it]
            if track.state != TrackState.Lost:
                track.mark_lost()
                lost_stracks.append(track)

        # Step 4: Deal with unconfirmed tracks, usually tracks with only one beginning frame
        detections_high_rem = [detections_high[i] for i in u_detection]
        dists = self._iou_distance(unconfirmed, detections_high_rem)
        matches, u_unconfirmed, u_detection_final = linear_assignment(dists, thresh=0.7)

        for itracked, idet in matches:
            unconfirmed[itracked].update(detections_high_rem[idet], self.frame_id)
            activated_starcks.append(unconfirmed[itracked])

        for it in u_unconfirmed:
            track = unconfirmed[it]
            track.mark_removed()
            removed_stracks.append(track)

        # Step 5: Init new stracks for remaining unassociated high-score detections
        for inew in u_detection_final:
            track = detections_high_rem[inew]
            if track.score >= self.track_thresh:
                track.activate(self.kalman_filter, self.frame_id)
                activated_starcks.append(track)

        # Step 6: Update state of lost tracks
        for track in self.lost_stracks:
            if self.frame_id - track.end_frame > self.max_time_lost:
                track.mark_removed()
                removed_stracks.append(track)

        self.tracked_stracks = [t for t in self.tracked_stracks if t.state == TrackState.Tracked]
        self.tracked_stracks = self._joint_stracks(self.tracked_stracks, activated_starcks)
        self.tracked_stracks = self._joint_stracks(self.tracked_stracks, refind_stracks)
        self.lost_stracks = self._sub_stracks(self.lost_stracks, self.tracked_stracks)
        self.lost_stracks.extend(lost_stracks)
        self.lost_stracks = self._sub_stracks(self.lost_stracks, self.removed_stracks)
        self.removed_stracks.extend(removed_stracks)
        self.tracked_stracks, self.lost_stracks = self._remove_duplicate_stracks(
            self.tracked_stracks, self.lost_stracks
        )

        output_stracks = [track for track in self.tracked_stracks if track.is_activated]
        return output_stracks

    @staticmethod
    def _joint_stracks(tlista: List[STrack], tlistb: List[STrack]) -> List[STrack]:
        exists = {}
        res = []
        for t in tlista:
            exists[t.track_id] = 1
            res.append(t)
        for t in tlistb:
            tid = t.track_id
            if not exists.get(tid, 0):
                exists[tid] = 1
                res.append(t)
        return res

    @staticmethod
    def _sub_stracks(tlista: List[STrack], tlistb: List[STrack]) -> List[STrack]:
        stracks = {}
        for t in tlista:
            stracks[t.track_id] = t
        for t in tlistb:
            tid = t.track_id
            if stracks.get(tid, 0):
                del stracks[tid]
        return list(stracks.values())

    @staticmethod
    def _remove_duplicate_stracks(stracksa: List[STrack], stracksb: List[STrack]) -> Tuple[List[STrack], List[STrack]]:
        pdist = bbox_ious(
            np.asarray([s.tlbr for s in stracksa]),
            np.asarray([s.tlbr for s in stracksb]),
        )
        pairs = np.where(pdist < 0.15)
        dupa, dupb = list(), list()
        for p, q in zip(*pairs):
            timep = stracksa[p].frame_id - stracksa[p].start_frame
            timeq = stracksb[q].frame_id - stracksb[q].start_frame
            if timep > timeq:
                dupb.append(q)
            else:
                dupa.append(p)
        resa = [t for i, t in enumerate(stracksa) if i not in dupa]
        resb = [t for i, t in enumerate(stracksb) if i not in dupb]
        return resa, resb

    @staticmethod
    def _iou_distance(atracks: List[STrack], btracks: List[STrack]) -> np.ndarray:
        if len(atracks) == 0 or len(btracks) == 0:
            return np.zeros((len(atracks), len(btracks)), dtype=float)
        atlbrs = np.asarray([track.tlbr for track in atracks])
        btlbrs = np.asarray([track.tlbr for track in btracks])
        ious = bbox_ious(atlbrs, btlbrs)
        return 1.0 - ious
