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

	def ensure_size(self, width: int, height: int) -> pygame.Surface:
		if self.surface is None or self.surface.get_size() != (width, height):
			self.surface = pygame.Surface((width, height), pygame.SRCALPHA)
		return self.surface

	def clear_controls_zone(self, controls_rect: pygame.Rect) -> None:
		if self.surface is None:
			return
		self.surface.fill((0, 0, 0, 0), controls_rect)

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
			color=draw_color,
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