from __future__ import annotations

class PSTConv:
    """Point spatio-temporal convolution over a point tube."""

    def __init__(
        self,
        spatial_radius: float,
        temporal_kernel_size: int,
    ) -> None:
        self.spatial_radius = spatial_radius
        self.temporal_kernel_size = temporal_kernel_size

    def forward(self, point_cloud_sequence):
        """Aggregate neighboring points over space and time."""
        return point_cloud_sequence


class PSTConvTranspose:
    """Upsample point features in space and time."""

    def forward(self, point_cloud_sequence):
        return point_cloud_sequence