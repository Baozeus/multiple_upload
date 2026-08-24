from __future__ import annotations

import pytest

from udm10.config import UploadPolicySettings
from udm10.domain import UploadRequest
from udm10.server.errors import ExtensionNotAllowed, FileTooLarge
from udm10.server.validation import UploadValidator


def _request(filename: str, size: int) -> UploadRequest:
    return UploadRequest(
        request_id="validation-1",
        batch_id="batch-validation",
        batch_total=1,
        filename=filename,
        size=size,
    )


@pytest.mark.parametrize("filename", ["ghi-chú.txt", "báo-cáo.pdf", "ảnh.jpg", "hợp-đồng.docx"])
def test_tc04_configured_supported_file_types_are_accepted(filename: str) -> None:
    validator = UploadValidator(
        UploadPolicySettings(None, 10, (".txt", ".pdf", ".jpg", ".docx"))
    )

    assert validator.validate(_request(filename, 128)).filename == filename


def test_tc04_invalid_extension_is_rejected_before_payload() -> None:
    validator = UploadValidator(
        UploadPolicySettings(None, None, (".txt", ".pdf", ".jpg", ".docx"))
    )

    with pytest.raises(ExtensionNotAllowed, match="Định dạng"):
        validator.validate(_request("không-hợp-lệ.exe", 128))


def test_tc05_file_over_configured_limit_is_rejected() -> None:
    validator = UploadValidator(UploadPolicySettings(None, 1, None))

    with pytest.raises(FileTooLarge, match="giới hạn dung lượng"):
        validator.validate(_request("lớn.pdf", 1024 * 1024 + 1))


def test_zero_byte_file_is_valid_at_policy_boundary() -> None:
    validator = UploadValidator(UploadPolicySettings(None, 1, (".txt",)))

    assert validator.validate(_request("rỗng.txt", 0)).size == 0
