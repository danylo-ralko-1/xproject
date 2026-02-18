"""Ingest command: parse all requirements from input/ and prepare context."""

import json
import click
from pathlib import Path

from core.config import (
    get_input_dir, get_output_path, update_state, update_status, save_project
)
from core.context import compute_input_hash, invalidate_downstream
from core.parser import (
    parse_directory, estimate_tokens, compute_file_hash, parsed_filename,
    ParsedFile,
)


def run(proj: dict) -> None:
    """
    Parse all files in input/ directory and produce:
      - output/parsed/<filename>.md  (one per source file)
      - output/requirements_manifest.json (metadata about parsed files)

    Only new/changed files are written. Removed files are cleaned up.
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

    # Detect per-file changes against previous manifest
    prev_hashes = _load_previous_hashes(proj)
    file_changes = _detect_changes(parsed, prev_hashes)
    new_files = [f for f, status in file_changes.items() if status == "new"]
    changed_files = [f for f, status in file_changes.items() if status == "changed"]
    removed_files = [f for f in prev_hashes if f not in file_changes]

    if prev_hashes and (new_files or changed_files or removed_files):
        click.secho(f"\n  Changes since last ingest:", fg="cyan")
        for f in new_files:
            click.echo(f"    + {f} (new)")
        for f in changed_files:
            click.echo(f"    ~ {f} (changed)")
        for f in removed_files:
            click.echo(f"    - {f} (removed)")

    # Ensure parsed directory exists
    parsed_dir = get_output_path(proj, "parsed")
    parsed_dir.mkdir(parents=True, exist_ok=True)

    # Write parsed .md files — only for new/changed files
    total_chars = 0
    written = 0
    for pf in parsed:
        if pf.error or pf.is_image or not pf.text.strip():
            continue
        out_name = parsed_filename(pf.filename)
        out_path = parsed_dir / out_name
        content = f"# {pf.filename} ({pf.format})\n\n{pf.text.strip()}"
        total_chars += len(content)

        change = file_changes.get(pf.filename, "new")
        if change in ("new", "changed"):
            out_path.write_text(content, encoding="utf-8")
            written += 1

    # Remove parsed files for deleted source files
    for fname in removed_files:
        old_path = parsed_dir / parsed_filename(fname)
        if old_path.exists():
            old_path.unlink()

    if written:
        click.secho(f"    Wrote {written} parsed file(s) to output/parsed/", fg="cyan")

    # Save image references for downstream use
    image_blocks = []
    if images:
        images_path = get_output_path(proj, "requirements_images.json")
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

    # Save manifest
    est_tokens = estimate_tokens("x" * total_chars)  # approximate
    manifest = {
        "project": project_name,
        "files": [_file_manifest(pf, file_changes.get(pf.filename, "new")) for pf in parsed],
        "summary": {
            "total_files": len(parsed),
            "successful": len(success),
            "errors": len(errors),
            "text_files": len(text_files),
            "image_files": len(images),
            "total_text_chars": total_chars,
            "estimated_tokens": est_tokens,
            "new_files": new_files,
            "changed_files": changed_files,
            "removed_files": removed_files,
        },
    }

    manifest_path = get_output_path(proj, "requirements_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    # Compute hash and update state
    req_hash = compute_input_hash(proj)

    # Invalidate downstream artifacts only if something actually changed
    if new_files or changed_files or removed_files or not prev_hashes:
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
    click.echo(f"    Parsed files: {parsed_dir}/ ({len(text_files)} files, {_human_size(total_chars)})")
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


def _file_manifest(pf: ParsedFile, change_status: str = "new") -> dict:
    """Create manifest entry for a parsed file."""
    entry = {
        "filename": pf.filename,
        "format": pf.format,
        "status": "error" if pf.error else "ok",
        "change": change_status,
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
        entry["content_hash"] = compute_file_hash(pf.text)
        entry["parsed_file"] = parsed_filename(pf.filename)
    entry.update({k: v for k, v in pf.metadata.items()})
    return entry


def _load_previous_hashes(proj: dict) -> dict[str, str]:
    """Load per-file content hashes from previous manifest (if exists)."""
    manifest_path = get_output_path(proj, "requirements_manifest.json")
    if not manifest_path.exists():
        return {}
    try:
        with open(manifest_path, "r") as f:
            prev = json.load(f)
        return {
            entry["filename"]: entry["content_hash"]
            for entry in prev.get("files", [])
            if "content_hash" in entry
        }
    except (json.JSONDecodeError, KeyError):
        return {}


def _detect_changes(parsed: list[ParsedFile], prev_hashes: dict[str, str]) -> dict[str, str]:
    """Compare current files against previous hashes. Returns {filename: 'new'|'changed'|'unchanged'}."""
    changes = {}
    for pf in parsed:
        if pf.error or pf.is_image:
            continue
        current_hash = compute_file_hash(pf.text)
        if pf.filename not in prev_hashes:
            changes[pf.filename] = "new"
        elif prev_hashes[pf.filename] != current_hash:
            changes[pf.filename] = "changed"
        else:
            changes[pf.filename] = "unchanged"
    return changes
