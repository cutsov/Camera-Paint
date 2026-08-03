import math


def is_finger_up(hand_landmarks, tip_idx: int, pip_idx: int) -> bool:
	"""Returns True when finger tip is above its PIP joint in image coordinates."""
	return hand_landmarks[tip_idx].y < hand_landmarks[pip_idx].y


def detect_mode(hand_landmarks, pinch_threshold: float) -> str:
	"""Detects drawing/erasing/dragging mode for one hand."""
	thumb_tip = hand_landmarks[4]
	index_tip = hand_landmarks[8]
	index_up = is_finger_up(hand_landmarks, 8, 6)
	middle_up = is_finger_up(hand_landmarks, 12, 10)
	ring_up = is_finger_up(hand_landmarks, 16, 14)
	pinky_up = is_finger_up(hand_landmarks, 20, 18)

	pinch_distance = math.hypot(thumb_tip.x - index_tip.x, thumb_tip.y - index_tip.y)
	if pinch_distance < pinch_threshold:
		return "dragging"
	# Open palm should reliably pause tools even when thumb orientation is ambiguous.
	if index_up and middle_up and ring_up and pinky_up:
		return "idle"
	# Eraser is intentionally strict: only index+middle fingers up.
	if index_up and middle_up and not ring_up and not pinky_up:
		return "erasing"
	if index_up and not middle_up and not ring_up and not pinky_up:
		return "drawing"
	return "idle"