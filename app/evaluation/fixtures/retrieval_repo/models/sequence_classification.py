from __future__ import annotations

from modules.pst_convolutions import PSTConv


class MSRAction:
    def __init__(self) -> None:
        self.stem = PSTConv(
            spatial_radius=0.5,
            temporal_kernel_size=3,
        )

    def forward(self, point_cloud_sequence):
        return self.stem.forward(
            point_cloud_sequence
        )