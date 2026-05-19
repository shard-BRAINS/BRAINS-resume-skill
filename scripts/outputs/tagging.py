"""Read/write DOCX custom properties for artifact tracking.

Custom properties live in the OPC part `docProps/custom.xml`. They are
invisible in the Word body, header, footer, and comment pane. Only the
*File -> Info -> Properties -> Advanced Properties -> Custom* dialog
shows them.

python-docx 1.2.0 does not expose a public API for custom properties,
so this module manipulates the underlying ZIP/XML directly.

| Property              | Type    | Notes                              |
| --------------------- | ------- | ---------------------------------- |
| BrainsArtifactId      | string  | 6-char Crockford base32 UID        |
| BrainsArtifactKind    | string  | 'resume' or 'cover-letter'         |
| BrainsJDId            | integer | tracker JD row id; 0 if unset      |
| BrainsParentId        | string  | parent UID; '' if root             |
| BrainsCreatedAt       | string  | ISO 8601 UTC                       |
| BrainsSkillVersion    | string  | e.g. '1.5.0'                       |

Absent jd_id stored as 0; absent parent_uid stored as ''. The reader
(read_artifact_meta in Task 7) converts these back to None.
"""
from __future__ import annotations

import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from xml.etree import ElementTree as ET


_CUSTOM_PROPS_PART = "docProps/custom.xml"
_CONTENT_TYPES_PART = "[Content_Types].xml"
_PACKAGE_RELS_PART = "_rels/.rels"

_CUSTOM_PROPS_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.custom-properties+xml"
)
_CUSTOM_PROPS_REL_TYPE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships/custom-properties"
)
_CUSTOM_PROPS_NS = (
    "http://schemas.openxmlformats.org/officeDocument/2006/custom-properties"
)
_VT_NS = "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes"
_CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

# Microsoft-defined FMTID for custom document properties.
_CUSTOM_FMTID = "{D5CDD505-2E9C-101B-9397-08002B2CF9AE}"


@dataclass
class ArtifactMeta:
    artifact_uid: str
    artifact_kind: Literal["resume", "cover-letter"]
    jd_id: int | None
    parent_uid: str | None
    created_at: str
    skill_version: str


def _meta_to_property_dict(meta: ArtifactMeta) -> dict[str, tuple[str, str]]:
    """Convert ArtifactMeta into {name: (vt_type, string_value)} entries.

    vt_type is the XML element name within the vt: namespace ('lpwstr' for
    strings, 'i4' for 32-bit integers).
    """
    return {
        "BrainsArtifactId":    ("lpwstr", meta.artifact_uid),
        "BrainsArtifactKind":  ("lpwstr", meta.artifact_kind),
        "BrainsJDId":          ("i4",     str(meta.jd_id if meta.jd_id is not None else 0)),
        "BrainsParentId":      ("lpwstr", meta.parent_uid if meta.parent_uid is not None else ""),
        "BrainsCreatedAt":     ("lpwstr", meta.created_at),
        "BrainsSkillVersion":  ("lpwstr", meta.skill_version),
    }


def _build_custom_xml(properties: dict[str, tuple[str, str]]) -> bytes:
    """Render the custom.xml part for the given properties.

    pids start at 2 (1 is reserved). Each property is assigned a unique pid
    in iteration order.
    """
    ET.register_namespace("", _CUSTOM_PROPS_NS)
    ET.register_namespace("vt", _VT_NS)
    root = ET.Element(f"{{{_CUSTOM_PROPS_NS}}}Properties")
    pid = 2
    for name, (vt_type, value) in properties.items():
        prop = ET.SubElement(
            root, f"{{{_CUSTOM_PROPS_NS}}}property",
            {"fmtid": _CUSTOM_FMTID, "pid": str(pid), "name": name},
        )
        val = ET.SubElement(prop, f"{{{_VT_NS}}}{vt_type}")
        val.text = value
        pid += 1
    return b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + ET.tostring(root, encoding="utf-8")


def _ensure_content_type_override(content_types_xml: bytes) -> bytes:
    """Ensure [Content_Types].xml has an Override for docProps/custom.xml."""
    ET.register_namespace("", _CT_NS)
    root = ET.fromstring(content_types_xml)
    override_partname = f"/{_CUSTOM_PROPS_PART}"
    # Look for existing override.
    for child in root.findall(f"{{{_CT_NS}}}Override"):
        if child.attrib.get("PartName") == override_partname:
            return content_types_xml  # already present
    # Append a new Override element.
    ET.SubElement(
        root, f"{{{_CT_NS}}}Override",
        {"PartName": override_partname, "ContentType": _CUSTOM_PROPS_CONTENT_TYPE},
    )
    return b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + ET.tostring(root, encoding="utf-8")


def _ensure_package_relationship(rels_xml: bytes) -> bytes:
    """Ensure _rels/.rels has a Relationship to docProps/custom.xml."""
    ET.register_namespace("", _REL_NS)
    root = ET.fromstring(rels_xml)
    target = _CUSTOM_PROPS_PART
    for child in root.findall(f"{{{_REL_NS}}}Relationship"):
        if child.attrib.get("Target") == target:
            return rels_xml  # already present
    # Find next available rId.
    existing_ids = {child.attrib.get("Id") for child in root.findall(f"{{{_REL_NS}}}Relationship")}
    n = 1
    while f"rId{n}" in existing_ids:
        n += 1
    ET.SubElement(
        root, f"{{{_REL_NS}}}Relationship",
        {"Id": f"rId{n}", "Type": _CUSTOM_PROPS_REL_TYPE, "Target": target},
    )
    return b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n' + ET.tostring(root, encoding="utf-8")


def write_artifact_meta(docx_path: Path | str, meta: ArtifactMeta) -> None:
    """Write the artifact metadata into the DOCX as custom properties.

    Operates by rewriting the ZIP: updates/inserts docProps/custom.xml,
    ensures [Content_Types].xml and _rels/.rels reference it.
    """
    docx_path = Path(docx_path)
    new_custom_xml = _build_custom_xml(_meta_to_property_dict(meta))

    tmp_fd, tmp_name = tempfile.mkstemp(suffix=".docx")
    os.close(tmp_fd)
    tmp_path = Path(tmp_name)
    try:
        with zipfile.ZipFile(docx_path, "r") as zin:
            with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_DEFLATED) as zout:
                for item in zin.infolist():
                    if item.filename == _CUSTOM_PROPS_PART:
                        continue  # we'll write the new one below
                    data = zin.read(item.filename)
                    if item.filename == _CONTENT_TYPES_PART:
                        data = _ensure_content_type_override(data)
                    elif item.filename == _PACKAGE_RELS_PART:
                        data = _ensure_package_relationship(data)
                    zout.writestr(item, data)
                zout.writestr(_CUSTOM_PROPS_PART, new_custom_xml)
        shutil.move(str(tmp_path), str(docx_path))
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _read_custom_properties_raw(docx_path: Path | str) -> dict[str, str]:
    """Read the custom-properties XML and return {name: raw_string_value}.

    Returns empty dict if docProps/custom.xml is not present. Used by
    tests and by Task 7's read_artifact_meta.
    """
    docx_path = Path(docx_path)
    with zipfile.ZipFile(docx_path, "r") as zf:
        if _CUSTOM_PROPS_PART not in zf.namelist():
            return {}
        raw = zf.read(_CUSTOM_PROPS_PART)
    root = ET.fromstring(raw)
    result: dict[str, str] = {}
    for prop in root.findall(f"{{{_CUSTOM_PROPS_NS}}}property"):
        name = prop.attrib.get("name")
        if not name:
            continue
        # The value child has a vt:* tag — strip namespace, use text.
        for child in prop:
            result[name] = (child.text or "")
            break
    return result
