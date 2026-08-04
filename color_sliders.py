from dataclasses import dataclass
import math
import pygame

from brushes import apply_saturation, get_color_from_position


@dataclass
class SliderState:
	lever_value: float = 0.5
	saturation_value: float = 1.0
	brightness_value: float = 1.0
	lever_grabbed: bool = False
	saturation_grabbed: bool = False
	brightness_grabbed: bool = False


@dataclass(frozen=True)
class SliderLayout:
	color_lever_rect: pygame.Rect
	saturation_lever_rect: pygame.Rect
	brightness_lever_rect: pygame.Rect
	drawing_rect: pygame.Rect
	controls_rect: pygame.Rect
	preview_rect: pygame.Rect
	margin: int
	gap: int


def build_slider_layout(width: int, height: int) -> SliderLayout:
	color_lever_width = max(20, width // 38)
	color_lever_height = max(165, int(height * 0.55))
	saturation_lever_width = color_lever_width
	saturation_lever_height = color_lever_height
	brightness_lever_width = color_lever_width
	brightness_lever_height = color_lever_height
	margin = 24
	gap = 26
	right_edge = width - margin
	color_lever_x = right_edge - (color_lever_width * 3 + gap * 2)
	saturation_lever_x = color_lever_x + color_lever_width + gap
	brightness_lever_x = saturation_lever_x + saturation_lever_width + gap
	preview_height = max(48, height // 12)
	color_lever_y = height - margin - preview_height - gap - color_lever_height
	saturation_lever_y = color_lever_y
	brightness_lever_y = color_lever_y

	color_lever_rect = pygame.Rect(color_lever_x, color_lever_y, color_lever_width, color_lever_height)
	saturation_lever_rect = pygame.Rect(saturation_lever_x, saturation_lever_y, saturation_lever_width, saturation_lever_height)
	brightness_lever_rect = pygame.Rect(brightness_lever_x, brightness_lever_y, brightness_lever_width, brightness_lever_height)

	controls_padding = max(18, gap)
	controls_left = max(0, color_lever_rect.left - controls_padding)
	drawing_rect = pygame.Rect(0, 0, max(1, controls_left), height)
	controls_rect = pygame.Rect(controls_left, 0, width - controls_left, height)

	preview_width = color_lever_width * 3 + gap * 2
	preview_rect = pygame.Rect(
		width - margin - preview_width,
		height - margin - preview_height,
		preview_width,
		preview_height,
	)

	return SliderLayout(
		color_lever_rect=color_lever_rect,
		saturation_lever_rect=saturation_lever_rect,
		brightness_lever_rect=brightness_lever_rect,
		drawing_rect=drawing_rect,
		controls_rect=controls_rect,
		preview_rect=preview_rect,
		margin=margin,
		gap=gap,
	)


def get_selected_color(state: SliderState) -> tuple[int, int, int]:
	base_color = get_color_from_position(1.0 - state.lever_value)
	desaturated_color = apply_saturation(base_color, state.saturation_value)
	return tuple(int(channel * state.brightness_value) for channel in desaturated_color)


def get_saturation_track_color(selected_color: tuple[int, int, int], saturation_value: float) -> tuple[int, int, int]:
	saturation_value = max(0.0, min(1.0, saturation_value))
	return apply_saturation(selected_color, saturation_value)


def _get_handle_geometry(lever_rect: pygame.Rect, value: float) -> tuple[int, int, int, int]:
	handle_width = max(34, lever_rect.width * 2)
	handle_height = max(18, lever_rect.width + 6)
	handle_x = lever_rect.centerx
	handle_y = int(lever_rect.bottom - value * lever_rect.height)
	return handle_width, handle_height, handle_x, handle_y


def update_drag(
	state: SliderState,
	layout: SliderLayout,
	drag_points: list[tuple[int, int]],
	is_touching_mode: bool,
) -> None:
	color_handle_width, color_handle_height, color_handle_x, color_handle_y = _get_handle_geometry(layout.color_lever_rect, state.lever_value)
	sat_handle_width, sat_handle_height, sat_handle_x, sat_handle_y = _get_handle_geometry(layout.saturation_lever_rect, state.saturation_value)
	bri_handle_width, bri_handle_height, bri_handle_x, bri_handle_y = _get_handle_geometry(layout.brightness_lever_rect, state.brightness_value)

	grab_radius = (max(color_handle_width, color_handle_height, sat_handle_width, sat_handle_height, bri_handle_width, bri_handle_height) // 2) + 16

	if is_touching_mode and drag_points:
		if not state.lever_grabbed and not state.saturation_grabbed and not state.brightness_grabbed:
			for point_x, point_y in drag_points:
				if math.hypot(point_x - color_handle_x, point_y - color_handle_y) <= grab_radius:
					state.lever_grabbed = True
					break
			if not state.lever_grabbed:
				for point_x, point_y in drag_points:
					if math.hypot(point_x - sat_handle_x, point_y - sat_handle_y) <= grab_radius:
						state.saturation_grabbed = True
						break
			if not state.lever_grabbed and not state.saturation_grabbed:
				for point_x, point_y in drag_points:
					if math.hypot(point_x - bri_handle_x, point_y - bri_handle_y) <= grab_radius:
						state.brightness_grabbed = True
						break

		if state.lever_grabbed:
			_, closest_y = min(
				drag_points,
				key=lambda p: math.hypot(p[0] - color_handle_x, p[1] - color_handle_y),
			)
			clamped_y = max(layout.color_lever_rect.top, min(layout.color_lever_rect.bottom, closest_y))
			state.lever_value = 1.0 - ((clamped_y - layout.color_lever_rect.top) / layout.color_lever_rect.height)
		elif state.saturation_grabbed:
			_, closest_y = min(
				drag_points,
				key=lambda p: math.hypot(p[0] - sat_handle_x, p[1] - sat_handle_y),
			)
			clamped_y = max(layout.saturation_lever_rect.top, min(layout.saturation_lever_rect.bottom, closest_y))
			state.saturation_value = 1.0 - ((clamped_y - layout.saturation_lever_rect.top) / layout.saturation_lever_rect.height)
		elif state.brightness_grabbed:
			_, closest_y = min(
				drag_points,
				key=lambda p: math.hypot(p[0] - bri_handle_x, p[1] - bri_handle_y),
			)
			clamped_y = max(layout.brightness_lever_rect.top, min(layout.brightness_lever_rect.bottom, closest_y))
			state.brightness_value = 1.0 - ((clamped_y - layout.brightness_lever_rect.top) / layout.brightness_lever_rect.height)
	else:
		state.lever_grabbed = False
		state.saturation_grabbed = False
		state.brightness_grabbed = False


def draw_sliders(
	screen: pygame.Surface,
	state: SliderState,
	layout: SliderLayout,
	selected_color: tuple[int, int, int],
) -> None:
	h = screen.get_height()
	lever_alpha = 165
	shadow_alpha = 120
	lever_layer_padding = 12
	lever_layer_rect = pygame.Rect(
		min(layout.color_lever_rect.left, layout.saturation_lever_rect.left, layout.brightness_lever_rect.left) - lever_layer_padding,
		min(layout.color_lever_rect.top, layout.saturation_lever_rect.top, layout.brightness_lever_rect.top) - lever_layer_padding,
		max(layout.color_lever_rect.right, layout.saturation_lever_rect.right, layout.brightness_lever_rect.right) - min(layout.color_lever_rect.left, layout.saturation_lever_rect.left, layout.brightness_lever_rect.left) + lever_layer_padding * 2,
		max(layout.color_lever_rect.bottom, layout.saturation_lever_rect.bottom, layout.brightness_lever_rect.bottom) - min(layout.color_lever_rect.top, layout.saturation_lever_rect.top, layout.brightness_lever_rect.top) + lever_layer_padding * 2,
	)
	lever_layer = pygame.Surface((lever_layer_rect.width, lever_layer_rect.height), pygame.SRCALPHA)

	track_left = layout.color_lever_rect.left - lever_layer_rect.left
	track_right = layout.color_lever_rect.right - lever_layer_rect.left
	track_top = layout.color_lever_rect.top - lever_layer_rect.top
	for i in range(layout.color_lever_rect.height):
		t = i / max(1, layout.color_lever_rect.height - 1)
		segment = t * 4
		if segment < 1:
			r, g, b = 255, int(255 * segment), 60
		elif segment < 2:
			r, g, b = int(255 * (2 - segment)), 255, 60
		elif segment < 3:
			r, g, b = 60, 255, int(255 * (segment - 2))
		else:
			r, g, b = 60, int(255 * (4 - segment)), 255
		base_track_color = apply_saturation((r, g, b), state.saturation_value)
		color = tuple(int(channel * state.brightness_value) for channel in base_track_color)
		pygame.draw.line(
			lever_layer,
			(*color, lever_alpha),
			(track_left, track_top + i),
			(track_right, track_top + i),
		)

	track_left = layout.saturation_lever_rect.left - lever_layer_rect.left
	track_right = layout.saturation_lever_rect.right - lever_layer_rect.left
	track_top = layout.saturation_lever_rect.top - lever_layer_rect.top
	for i in range(layout.saturation_lever_rect.height):
		t = i / max(1, layout.saturation_lever_rect.height - 1)
		saturation_value = 1.0 - t
		color = get_saturation_track_color(selected_color, saturation_value)
		pygame.draw.line(
			lever_layer,
			(*color, lever_alpha),
			(track_left, track_top + i),
			(track_right, track_top + i),
		)

	track_left = layout.brightness_lever_rect.left - lever_layer_rect.left
	track_right = layout.brightness_lever_rect.right - lever_layer_rect.left
	track_top = layout.brightness_lever_rect.top - lever_layer_rect.top
	for i in range(layout.brightness_lever_rect.height):
		t = i / max(1, layout.brightness_lever_rect.height - 1)
		mix = 1.0 - t
		color = tuple(int(channel * mix) for channel in selected_color)
		pygame.draw.line(
			lever_layer,
			(*color, lever_alpha),
			(track_left, track_top + i),
			(track_right, track_top + i),
		)

	color_handle_width, color_handle_height, color_handle_x, color_handle_y = _get_handle_geometry(layout.color_lever_rect, state.lever_value)
	sat_handle_width, sat_handle_height, sat_handle_x, sat_handle_y = _get_handle_geometry(layout.saturation_lever_rect, state.saturation_value)
	bri_handle_width, bri_handle_height, bri_handle_x, bri_handle_y = _get_handle_geometry(layout.brightness_lever_rect, state.brightness_value)

	handle_color = (255, 245, 245) if state.lever_grabbed else (245, 245, 245)
	handle_rect = pygame.Rect(0, 0, color_handle_width, color_handle_height)
	handle_rect.center = (color_handle_x, color_handle_y)
	shadow_rect = handle_rect.inflate(6, 6)
	shadow_rect.move_ip(-lever_layer_rect.left, -lever_layer_rect.top)
	handle_rect.move_ip(-lever_layer_rect.left, -lever_layer_rect.top)
	pygame.draw.rect(lever_layer, (30, 30, 30, shadow_alpha), shadow_rect, border_radius=6)
	pygame.draw.rect(lever_layer, (*handle_color, lever_alpha), handle_rect, border_radius=5)

	handle_color = (255, 245, 245) if state.saturation_grabbed else (245, 245, 245)
	handle_rect = pygame.Rect(0, 0, sat_handle_width, sat_handle_height)
	handle_rect.center = (sat_handle_x, sat_handle_y)
	shadow_rect = handle_rect.inflate(6, 6)
	shadow_rect.move_ip(-lever_layer_rect.left, -lever_layer_rect.top)
	handle_rect.move_ip(-lever_layer_rect.left, -lever_layer_rect.top)
	pygame.draw.rect(lever_layer, (30, 30, 30, shadow_alpha), shadow_rect, border_radius=6)
	pygame.draw.rect(lever_layer, (*handle_color, lever_alpha), handle_rect, border_radius=5)

	handle_color = (255, 245, 245) if state.brightness_grabbed else (245, 245, 245)
	handle_rect = pygame.Rect(0, 0, bri_handle_width, bri_handle_height)
	handle_rect.center = (bri_handle_x, bri_handle_y)
	shadow_rect = handle_rect.inflate(6, 6)
	shadow_rect.move_ip(-lever_layer_rect.left, -lever_layer_rect.top)
	handle_rect.move_ip(-lever_layer_rect.left, -lever_layer_rect.top)
	pygame.draw.rect(lever_layer, (30, 30, 30, shadow_alpha), shadow_rect, border_radius=6)
	pygame.draw.rect(lever_layer, (*handle_color, lever_alpha), handle_rect, border_radius=5)

	screen.blit(lever_layer, lever_layer_rect.topleft)

	controls_overlay = pygame.Surface((layout.controls_rect.width, layout.controls_rect.height), pygame.SRCALPHA)
	controls_overlay.fill((10, 10, 10, 55))
	screen.blit(controls_overlay, layout.controls_rect.topleft)
	pygame.draw.line(screen, (230, 230, 230), (layout.controls_rect.left, 0), (layout.controls_rect.left, h), 2)

	pygame.draw.rect(screen, selected_color, layout.preview_rect)
	pygame.draw.rect(screen, (240, 240, 240), layout.preview_rect, 2)