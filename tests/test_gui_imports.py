from __future__ import annotations


def test_gui_modules_import() -> None:
    import sdt_batch_exporter.gui.app  # noqa: F401
    import sdt_batch_exporter.gui.color_bar  # noqa: F401
    import sdt_batch_exporter.gui.file_table  # noqa: F401
    import sdt_batch_exporter.gui.main_window  # noqa: F401
    import sdt_batch_exporter.gui.metadata_panel  # noqa: F401
    import sdt_batch_exporter.gui.png_export_worker  # noqa: F401
    import sdt_batch_exporter.gui.png_exporter  # noqa: F401
    import sdt_batch_exporter.gui.preview_compositor  # noqa: F401
    import sdt_batch_exporter.gui.preview_image  # noqa: F401
    import sdt_batch_exporter.gui.preview_options  # noqa: F401
    import sdt_batch_exporter.gui.preview_panel  # noqa: F401
    import sdt_batch_exporter.gui.preview_rendering  # noqa: F401
    import sdt_batch_exporter.gui.preview_worker  # noqa: F401
    import sdt_batch_exporter.gui.scale_bar  # noqa: F401
