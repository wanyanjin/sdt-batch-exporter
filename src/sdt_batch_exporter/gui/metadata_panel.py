"""Widget for displaying axis info, intensity stats, and metadata."""

from __future__ import annotations

from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from sdt_batch_exporter.models.sdt import PreviewData


class MetadataPanel(QWidget):
    """Display axis inference results, intensity stats, and metadata summary."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tree = QTreeWidget(self)
        self._tree.setColumnCount(2)
        self._tree.setHeaderLabels(["Key", "Value"])
        self._tree.header().setStretchLastSection(True)
        layout.addWidget(self._tree)

    def set_preview(self, preview: PreviewData) -> None:
        """Populate tree with data from *preview*."""
        self.clear()

        ai = preview.axis_info
        self._add_section(
            "Axis Info",
            {
                "axis_order": str(list(ai.axis_order)),
                "time_axis_index": str(ai.time_axis_index),
                "spatial_axes": str(list(ai.spatial_axes)),
                "inference_source": ai.inference_source,
                "axis_inference_status": str(ai.axis_inference_status),
                "is_exportable_intensity": str(ai.is_exportable_intensity),
                "skipped_intensity_export": str(ai.skipped_intensity_export),
                "skip_reason": str(ai.skip_reason),
            },
        )

        if preview.intensity_stats:
            self._add_section(
                "Intensity Stats",
                {k: str(v) for k, v in preview.intensity_stats.items()},
            )

        if preview.metadata_summary:
            self._add_section(
                "Metadata",
                {k: str(v) for k, v in preview.metadata_summary.items()},
            )

        self._tree.expandAll()
        self._tree.resizeColumnToContents(0)

    def clear(self) -> None:
        """Remove all tree items."""
        self._tree.clear()

    def _add_section(self, title: str, data: dict[str, str]) -> QTreeWidgetItem:
        section = QTreeWidgetItem(self._tree, [title, ""])
        section.setExpanded(True)
        for key, value in data.items():
            QTreeWidgetItem(section, [key, value])
        return section
