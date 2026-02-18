"""Ingest command: parse all requirements from input/ and prepare context."""

import json
import click
from pathlib import Path

from core.config import (
    get_input_dir, get_output_path, update_state, update_status, save_project
)
from core.context import compute_input_hash, invalidate_downstream
from core.parser import (
    parse_directory, build_context, build_sections, estimate_tokens,
    ParsedFile, CONTEXT_CHAR_THRESHOLD,
)


def run(proj: dict) -> None:
    """
    Parse all files in input/ directory and produce:
      - output/requirements_context.md  (combined text for downstream prompts)
      - output/requirements_manifest.json (metadata about parsed files)

    Updates project state with requirements hash.
    """
    input_dir = get_input_dir(proj)
    project_name = proj["project"]

    click.secho(f"\n  Ingesting requirements for '{project_name}'", bold=True)
    click.echo(f"  Source: {input_dir}\n")

    # Check for files
    if not input_dir.exists() or not any(input_dir.rglob("*")):
        click.secho("  ✗ No files found in input/ directory", fg="red")
        click.echo(f"    Drop requirement files into: {input_dir}")
        return

    # Parse all files
    parsed = parse_directory(input_dir)

    if not parsed:
        click.secho("  ✗ No supported files found", fg="red")
        return

    # Report results
    success = [p for p in parsed if not p.error]
    errors = [p for p in parsed if p.error]
    images = [p for p in success if p.is_image]
    text_files = [p for p in success if not p.is_image]

    click.secho(f"  Parsed {len(success)} files:", fg="green")
    for pf in success:
        size = _content_size(pf)
        click.echo(f"    ✓ {pf.filename:40s} ({pf.format}, {size})")

    if errors:
        click.secho(f"\n  Skipped {len(errors)} files:", fg="yellow")
        for pf in errors:
            click.echo(f"    ⚠ {pf.filename:40s} ({pf.error})")

    # Build combined context
    text_context, image_blocks = build_context(parsed)

    if not text_context and not image_blocks:
        click.secho("\n  ✗ No content extracted from any file", fg="red")
        return

    # Save requirements context (text) — always written regardless of strategy
    ctx_path = get_output_path(proj, "requirements_context.md")
    ctx_path.parent.mkdir(parents=True, exist_ok=True)
    ctx_path.write_text(text_context, encoding="utf-8")

    # Determine context strategy based on size
    total_chars = len(text_context)
    est_tokens = estimate_tokens(text_context)
    sections_meta = []

    if total_chars > CONTEXT_CHAR_THRESHOLD:
        context_strategy = "sectioned"
        click.secho(
            f"\n  ⚠ Context is large ({_human_size(total_chars)}, ~{est_tokens:,} tokens). "
            f"Splitting into per-file sections for incremental reading.",
            fg="yellow",
        )
        sections = build_sections(parsed)
        sections_dir = ctx_path.parent / "requirements_sections"
        # Clear old sections if re-ingesting
        if sections_dir.exists():
            for old in sections_dir.iterdir():
                old.unlink()
        sections_dir.mkdir(parents=True, exist_ok=True)
        for sec in sections:
            sec_path = sections_dir / sec["filename"]
            sec_path.write_text(sec["content"], encoding="utf-8")
            sections_meta.append({
                "index": sec["index"],
                "filename": sec["filename"],
                "source": sec["source"],
                "format": sec["format"],
                "chars": sec["chars"],
                "estimated_tokens": sec["estimated_tokens"],
            })
        click.secho(f"    Created {len(sections)} section files in requirements_sections/", fg="yellow")
    else:
        context_strategy = "full"
        # Clean up sections dir if it exists from a previous larger ingest
        sections_dir = ctx_path.parent / "requirements_sections"
        if sections_dir.exists():
            for old in sections_dir.iterdir():
                old.unlink()
            sections_dir.rmdir()

    # Save manifest (metadata about what was parsed)
    manifest = {
        "project": project_name,
        "files": [_file_manifest(pf) for pf in parsed],
        "summary": {
            "total_files": len(parsed),
            "successful": len(success),
            "errors": len(errors),
            "text_files": len(text_files),
            "image_files": len(images),
            "total_text_chars": total_chars,
            "estimated_tokens": est_tokens,
            "context_strategy": context_strategy,
        },
    }
    if sections_meta:
        manifest["sections"] = sections_meta

    manifest_path = get_output_path(proj, "requirements_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # If there are images, save their references for downstream use
    if image_blocks:
        images_path = get_output_path(proj, "requirements_images.json")
        # Save just metadata, not the full base64 (too large for JSON)
        img_refs = []
        for pf in images:
            img_refs.append({
                "filename": pf.filename,
                "media_type": pf.image_media_type,
                "size_bytes": pf.metadata.get("size_bytes", 0),
                "path": str(input_dir / pf.filename),
            })
        with open(images_path, "w", encoding="utf-8") as f:
            json.dump(img_refs, f, indent=2)

        click.secho(f"\n  📷 {len(images)} image(s) detected — will be sent to Claude vision", fg="cyan")

    # Compute hash and update state
    req_hash = compute_input_hash(proj)

    # Invalidate downstream artifacts since requirements changed
    invalidate_downstream(proj, "ingest")

    # Update state
    update_state(
        proj,
        requirements_hash=req_hash,
        requirements_ingested=True,
    )
    update_status(proj, "discovery")

    # Summary
    click.secho(f"\n  ✓ Requirements ingested successfully", fg="green", bold=True)
    click.echo(f"    Context: {ctx_path} ({_human_size(len(text_context))})")
    click.echo(f"    Manifest: {manifest_path}")
    click.echo(f"    Hash: {req_hash}")
    click.echo(f"\n    Next step: presales discover {project_name}")


def _content_size(pf: ParsedFile) -> str:
    """Human-readable content size."""
    if pf.is_image:
        size = pf.metadata.get("size_bytes", 0)
        return _human_size(size)
    return _human_size(len(pf.text))


def _human_size(n: int) -> str:
    """Convert byte/char count to human-readable."""
    if n < 1024:
        return f"{n} chars"
    elif n < 1024 * 1024:
        return f"{n/1024:.1f} KB"
    else:
        return f"{n/(1024*1024):.1f} MB"


def _file_manifest(pf: ParsedFile) -> dict:
    """Create manifest entry for a parsed file."""
    entry = {
        "filename": pf.filename,
        "format": pf.format,
        "status": "error" if pf.error else "ok",
    }
    if pf.error:
        entry["error"] = pf.error
    if pf.is_image:
        entry["type"] = "image"
        entry["media_type"] = pf.image_media_type
    else:
        entry["type"] = "text"
        entry["text_length"] = len(pf.text)
        entry["estimated_tokens"] = estimate_tokens(pf.text)
    entry.update({k: v for k, v in pf.metadata.items()})
    return entry
