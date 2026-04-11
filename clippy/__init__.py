"""Clippy application package root.

Single responsibility: mark the ``clippy`` directory as a Python package so
absolute imports (for example ``from clippy.app import ...``) resolve correctly
across the menubar app, chat UI bridge, and reminder subsystems.
"""
