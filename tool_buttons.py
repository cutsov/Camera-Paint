import pygame


class ToolButton:
	"""A one-shot button that cycles through drawing tool labels."""

	def __init__(
		self,
		x: int,
		y: int,
		width: int,
		height: int,
		labels: list[str] | None = None,
	) -> None:
		self.rect = pygame.Rect(x, y, width, height)
		self.labels = labels or ["Brush", "Rect.", "Ellipse"]
		self.current_index = 0
		self._was_touched = False

	@property
	def label(self) -> str:
		return self.labels[self.current_index]

	def handle_touch(self, touch_points, is_touching_mode: bool) -> bool:
		if not is_touching_mode:
			self._was_touched = False
			return False

		inside_button = any(self.rect.collidepoint(point) for point in touch_points)
		if inside_button and not self._was_touched:
			self._was_touched = True
			self.current_index = (self.current_index + 1) % len(self.labels)
			return True

		if not inside_button:
			self._was_touched = False
		return False

	def draw(self, screen, font) -> None:
		panel = pygame.Surface((self.rect.width, self.rect.height), pygame.SRCALPHA)
		panel.fill((10, 10, 10, 60))
		screen.blit(panel, self.rect.topleft)
		pygame.draw.rect(screen, (230, 230, 230), self.rect, 2, border_radius=8)

		text_font = pygame.font.SysFont(None, 24)
		text_surface = text_font.render(self.label, True, (255, 255, 255))
		text_rect = text_surface.get_rect(center=self.rect.center)
		screen.blit(text_surface, text_rect)
