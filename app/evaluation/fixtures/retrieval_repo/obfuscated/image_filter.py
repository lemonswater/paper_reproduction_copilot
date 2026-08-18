from __future__ import annotations

class ImageSmoother:
    """Average nearby image pixels independently in each frame."""

    def forward(self, video):
        spatial_average = video.mean(
            axis=(-1, -2),
            keepdims=True,
        )
        return video - spatial_average