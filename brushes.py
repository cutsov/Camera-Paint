from dataclasses import dataclass
import math
import pygame


@dataclass(frozen=True)
class BrushConfig:
	pinch_threshold: float = 0.05
	draw_radius: int = 6
	erase_radius: int = 20


def get_color_from_position(position: float) -> tuple[int, int, int]:
	"""Returns a rainbow color for a 0..1 lever position."""
	segment = max(0.0, min(1.0, position)) * 4
	if segment < 1:
		return (255, int(255 * segment), 60)
	if segment < 2:
		return (int(255 * (2 - segment)), 255, 60)
	if segment < 3:
		return (60, 255, int(255 * (segment - 2)))
	return (60, int(255 * (4 - segment)), 255)


def apply_saturation(color: tuple[int, int, int], saturation: float) -> tuple[int, int, int]:
	"""Desaturates a color toward gray for a 0..1 saturation value."""
	saturation = max(0.0, min(1.0, saturation))
	gray = sum(color) // 3
	return tuple(int(channel * saturation + gray * (1.0 - saturation)) for channel in color)


def draw_round_brush(
	surface: pygame.Surface,
	color: tuple[int, int, int] | tuple[int, int, int, int],
	start: tuple[int, int],
	end: tuple[int, int],
	radius: int,
) -> None:
	"""Draws a smooth round brush stroke with a fixed radius."""
	if start == end:
		pygame.draw.circle(surface, color, start, radius)
		return

	dx = end[0] - start[0]
	dy = end[1] - start[1]
	distance = max(1, int(math.hypot(dx, dy)))
	step_size = max(1, min(3, radius // 2))
	steps = max(1, distance // step_size)
	for step in range(steps + 1):
		t = step / steps
		x = int(start[0] + dx * t)
		y = int(start[1] + dy * t)
		pygame.draw.circle(surface, color, (x, y), radius)