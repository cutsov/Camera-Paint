from dataclasses import dataclass, field
import math
import pygame

from brushes import draw_round_brush


def draw_points_with_stable_tracks(
	surface: pygame.Surface,
	points: list[tuple[int, int]],
	tracks: dict[int, tuple[int, int]],
	next_track_id: int,
	color: tuple[int, int, int] | tuple[int, int, int, int],
	radius: int,
	max_link_distance: float,
) -> int:
	"""Matches points to previous tracks to avoid cross-hand line jumps between frames."""
	candidates = []
	for track_id, previous_point in tracks.items():
		for point_index, point in enumerate(points):
			distance = math.hypot(point[0] - previous_point[0], point[1] - previous_point[1])
			if distance <= max_link_distance:
				candidates.append((distance, track_id, point_index))

	candidates.sort(key=lambda item: item[0])
	used_tracks = set()
	used_points = set()
	updated_tracks = {}

	for _, track_id, point_index in candidates:
		if track_id in used_tracks or point_index in used_points:
			continue
		previous_point = tracks[track_id]
		point = points[point_index]
		draw_round_brush(surface, color, previous_point, point, radius)
		updated_tracks[track_id] = point
		used_tracks.add(track_id)
		used_points.add(point_index)

	for point_index, point in enumerate(points):
		if point_index in used_points:
			continue
		pygame.draw.circle(surface, color, point, radius)
		updated_tracks[next_track_id] = point
		next_track_id += 1

	tracks.clear()
	tracks.update(updated_tracks)
	return next_track_id


@dataclass
class CanvasState:
	surface: pygame.Surface | None = None
	draw_tracks: dict[int, tuple[int, int]] = field(default_factory=dict)
	erase_tracks: dict[int, tuple[int, int]] = field(default_factory=dict)
	next_draw_track_id: int = 0
	next_erase_track_id: int = 0
	draw_alpha: int = 165
	active_shape_tool: str | None = None
	active_shape_start: tuple[int, int] | None = None
	active_shape_end: tuple[int, int] | None = None
	active_shape_color: tuple[int, int, int] = (255, 255, 255)

	def ensure_size(self, width: int, height: int) -> pygame.Surface:
		if self.surface is None or self.surface.get_size() != (width, height):
			self.surface = pygame.Surface((width, height), pygame.SRCALPHA)
		return self.surface

	def clear_controls_zone(self, controls_rect: pygame.Rect) -> None:
		if self.surface is None:
			return
		self.surface.fill((0, 0, 0, 0), controls_rect)

	def _active_shape_rect(self) -> pygame.Rect | None:
		if self.active_shape_start is None or self.active_shape_end is None:
			return None

		x1, y1 = self.active_shape_start
		x2, y2 = self.active_shape_end
		left = min(x1, x2)
		top = min(y1, y2)
		width = max(1, abs(x2 - x1))
		height = max(1, abs(y2 - y1))
		return pygame.Rect(left, top, width, height)

	def _draw_shape(self, surface: pygame.Surface, tool: str, color: tuple[int, int, int] | tuple[int, int, int, int]) -> None:
		rect = self._active_shape_rect()
		if rect is None:
			return

		if tool == "rect":
			pygame.draw.rect(surface, color, rect)
		elif tool == "ellipse":
			pygame.draw.ellipse(surface, color, rect)

	def _clear_active_shape(self) -> None:
		self.active_shape_tool = None
		self.active_shape_start = None
		self.active_shape_end = None

	def _with_draw_alpha(self, color: tuple[int, int, int]) -> tuple[int, int, int, int]:
		alpha = max(0, min(255, self.draw_alpha))
		return (color[0], color[1], color[2], alpha)

	def commit_active_shape(self) -> None:
		if self.surface is None or self.active_shape_tool is None:
			return

		self._draw_shape(self.surface, self.active_shape_tool, self._with_draw_alpha(self.active_shape_color))
		self._clear_active_shape()

	def update_active_shape(
		self,
		active_tool: str,
		drawing_points: list[tuple[int, int]],
		is_drawing_mode: bool,
		draw_color: tuple[int, int, int],
	) -> None:
		shape_tools = {"rect", "ellipse"}
		if active_tool not in shape_tools:
			self.commit_active_shape()
			return

		if not is_drawing_mode or not drawing_points:
			self.commit_active_shape()
			return

		if self.active_shape_tool != active_tool or self.active_shape_start is None:
			shape_point = drawing_points[0]
			self.active_shape_tool = active_tool
			self.active_shape_start = shape_point
			self.active_shape_end = shape_point
			self.active_shape_color = draw_color
			return

		anchor = self.active_shape_end or self.active_shape_start
		shape_point = min(
			drawing_points,
			key=lambda point: (point[0] - anchor[0]) ** 2 + (point[1] - anchor[1]) ** 2,
		)
		self.active_shape_end = shape_point
		self.active_shape_color = draw_color

	def draw_active_shape_preview(self, target_surface: pygame.Surface) -> None:
		if self.active_shape_tool is None:
			return

		preview_surface = pygame.Surface(target_surface.get_size(), pygame.SRCALPHA)
		preview_color = (*self.active_shape_color, 110)
		self._draw_shape(preview_surface, self.active_shape_tool, preview_color)
		target_surface.blit(preview_surface, (0, 0))

	def apply_strokes(
		self,
		drawing_points: list[tuple[int, int]],
		erasing_points: list[tuple[int, int]],
		draw_color: tuple[int, int, int],
		draw_radius: int,
		erase_radius: int,
	) -> None:
		if self.surface is None:
			return

		self.next_draw_track_id = draw_points_with_stable_tracks(
			surface=self.surface,
			points=drawing_points,
			tracks=self.draw_tracks,
			next_track_id=self.next_draw_track_id,
			color=self._with_draw_alpha(draw_color),
			radius=draw_radius,
			max_link_distance=max(36.0, draw_radius * 8.0),
		)

		self.next_erase_track_id = draw_points_with_stable_tracks(
			surface=self.surface,
			points=erasing_points,
			tracks=self.erase_tracks,
			next_track_id=self.next_erase_track_id,
			color=(0, 0, 0, 0),
			radius=erase_radius,
			max_link_distance=max(80.0, erase_radius * 2.0),
		)