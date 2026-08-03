import cv2
import mediapipe as mp
import mediapipe.tasks as mp_tasks
import pygame
from pathlib import Path
import time
import urllib.request
from brushes import BrushConfig
from canvas import CanvasState
from color_sliders import SliderState, build_slider_layout, draw_sliders, get_selected_color, update_drag
from mode_selector import detect_mode


def ensure_model_download(model_path: Path) -> None:
	if model_path.exists():
		return

	model_path.parent.mkdir(parents=True, exist_ok=True)
	url = "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
	print(f"Model file not found at {model_path}. Downloading...")
	try:
		urllib.request.urlretrieve(url, model_path)
		print(f"Model downloaded to {model_path}")
	except Exception as exc:
		raise RuntimeError(f"Unable to download model: {exc}") from exc


def main() -> None:
	cap = cv2.VideoCapture(0)
	window_name = "Cam"
	aa_scale = 2

	if not cap.isOpened():
		print("Error. Unable to open the camera")
		return

	model_path = Path(__file__).resolve().parent / "hand_landmarker.task"
	try:
		ensure_model_download(model_path)
	except RuntimeError as exc:
		print(f"Error: {exc}")
		cap.release()
		return

	pygame.init()
	screen = None
	overlay_hi = None
	clock = pygame.time.Clock()
	font = pygame.font.SysFont(None, 32)
	brush_config = BrushConfig()
	slider_state = SliderState()
	canvas_state = CanvasState()

	base_options = mp_tasks.BaseOptions(model_asset_path=str(model_path))
	options = mp_tasks.vision.HandLandmarkerOptions(
		base_options=base_options,
		running_mode=mp_tasks.vision.RunningMode.VIDEO,
		num_hands=10,
		min_hand_detection_confidence=0.5,
		min_hand_presence_confidence=0.5,
		min_tracking_confidence=0.5,
	)

	with mp_tasks.vision.HandLandmarker.create_from_options(options) as landmarker:
		print("Camera started. Press q or ESC to exit")
		running = True

		while running:
			for event in pygame.event.get():
				if event.type == pygame.QUIT:
					running = False
				elif event.type == pygame.KEYDOWN and event.key in (pygame.K_q, pygame.K_ESCAPE):
					running = False

			ret, frame = cap.read()
			if not ret:
				print("Error: failed to read frame")
				break

			frame = cv2.flip(frame, 1)
			rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
			mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
			timestamp_ms = int(time.monotonic() * 1000)
			result = landmarker.detect_for_video(mp_image, timestamp_ms)

			h, w = frame.shape[:2]
			if screen is None:
				screen = pygame.display.set_mode((w, h))
				overlay_hi = pygame.Surface((w * aa_scale, h * aa_scale), pygame.SRCALPHA)
				pygame.display.set_caption(window_name)

			draw_canvas = canvas_state.ensure_size(w, h)
			slider_layout = build_slider_layout(w, h)
			canvas_state.clear_controls_zone(slider_layout.controls_rect)

			frame_surface = pygame.image.frombuffer(rgb_frame.tobytes(), (w, h), "RGB")
			screen.blit(frame_surface, (0, 0))
			overlay_hi.fill((0, 0, 0, 0))
			mode = "idle"
			drag_points = []

			selected_color = get_selected_color(slider_state)

			brush_radius = brush_config.draw_radius
			erase_radius = brush_config.erase_radius
			drawing_points = []
			erasing_points = []
			dragging_detected = False
			drawing_detected = False
			erasing_detected = False
			for hand_landmarks in (result.hand_landmarks or []):
				detected_mode = detect_mode(hand_landmarks, brush_config.pinch_threshold)
				if detected_mode == "dragging":
					thumb_tip = hand_landmarks[4]
					index_tip = hand_landmarks[8]
					pinch_x = int(((thumb_tip.x + index_tip.x) * 0.5) * w)
					pinch_y = int(((thumb_tip.y + index_tip.y) * 0.5) * h)
					if slider_layout.controls_rect.collidepoint(pinch_x, pinch_y):
						drag_points.append((pinch_x, pinch_y))
						dragging_detected = True
				elif detected_mode == "drawing":
					index_tip = hand_landmarks[8]
					point_x = int(index_tip.x * w)
					point_y = int(index_tip.y * h)
					if slider_layout.drawing_rect.collidepoint(point_x, point_y):
						drawing_points.append((point_x, point_y))
						drawing_detected = True
				elif detected_mode == "erasing":
					index_tip = hand_landmarks[8]
					middle_tip = hand_landmarks[12]
					point_x = int(((index_tip.x + middle_tip.x) * 0.5) * w)
					point_y = int(((index_tip.y + middle_tip.y) * 0.5) * h)
					if slider_layout.drawing_rect.collidepoint(point_x, point_y):
						erasing_points.append((point_x, point_y))
						erasing_detected = True

			# Priority: dragging > erasing > drawing > idle
			if dragging_detected:
				mode = "dragging"
			elif erasing_detected:
				mode = "erasing"
			elif drawing_detected:
				mode = "drawing"

			canvas_state.apply_strokes(
				drawing_points=drawing_points,
				erasing_points=erasing_points,
				draw_color=selected_color,
				draw_radius=brush_radius,
				erase_radius=erase_radius,
			)

			update_drag(
				state=slider_state,
				layout=slider_layout,
				drag_points=drag_points,
				is_dragging_mode=(mode == "dragging"),
			)

			screen.blit(draw_canvas, (0, 0))
			draw_sliders(
				screen=screen,
				state=slider_state,
				layout=slider_layout,
				selected_color=selected_color,
			)

			if mode == "dragging":
				for point_x, point_y in drag_points:
					pygame.draw.circle(screen, (255, 220, 90), (point_x, point_y), 6)
			if mode == "drawing" and drawing_points:
				for point_x, point_y in drawing_points:
					pygame.draw.circle(screen, (255, 255, 255), (point_x, point_y), brush_radius + 5, 2)
			if mode == "erasing" and erasing_points:
				for point_x, point_y in erasing_points:
					pygame.draw.circle(screen, (255, 60, 60), (point_x, point_y), erase_radius + 5, 2)

			smoothed_overlay = pygame.transform.smoothscale(overlay_hi, (w, h))
			screen.blit(smoothed_overlay, (0, 0))

			status_text = f"mode: {mode}"
			text_surface = font.render(status_text, True, (255, 255, 255))
			text_x = 12
			text_y = 12
			screen.blit(text_surface, (text_x, text_y))

			pygame.display.flip()
			clock.tick(60)

	cap.release()
	pygame.quit()
	print("Camera closed")


if __name__ == "__main__":
	main()
