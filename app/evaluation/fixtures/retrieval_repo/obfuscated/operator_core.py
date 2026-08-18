from __future__ import annotations

def collect_local_groups(
    coordinates,
    radius,
):
    """Return nearby point indices for every frame."""

    return radius_neighbors(
        coordinates,
        radius,
    )


class LocalMixer:
    """
    Aggregate geometric neighborhoods over adjacent frames.

    The deliberately generic name does not expose the paper module name.
    """

    def forward(
        self,
        frame_coordinates,
        frame_features,
    ):
        groups = collect_local_groups(
            frame_coordinates,
            radius=0.5,
        )
        motion_offsets = (
            frame_coordinates[:, 1:]
            - frame_coordinates[:, :-1]
        )
        return weighted_pool(
            frame_features,
            groups,
            motion_offsets,
        )