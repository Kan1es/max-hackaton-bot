import pytest
from pydantic import ValidationError

from app.core.options import OTHER_REGION_LABEL
from app.schemas.application import ApplicationCreate
from app.schemas.profile import ProfileUpsert


class TestProfileUpsert:
    def test_canonical_values_pass(self):
        payload = ProfileUpsert(status="ИП", industry="IT", priority="Развитие", region="Тверь")
        assert payload.status == "ИП"

    @pytest.mark.parametrize("field,value", [
        ("status", "Директор завода"),
        ("industry", "Космонавтика"),
        ("priority", "Всё сразу"),
    ])
    def test_values_outside_the_option_list_are_rejected(self, field, value):
        with pytest.raises(ValidationError):
            ProfileUpsert(**{field: value})

    def test_placeholder_region_is_rejected(self):
        """"Другой регион" is a button label, never a real answer."""
        with pytest.raises(ValidationError):
            ProfileUpsert(region=OTHER_REGION_LABEL)

    def test_blank_region_is_rejected(self):
        with pytest.raises(ValidationError):
            ProfileUpsert(region="   ")

    def test_partial_payloads_are_allowed(self):
        assert ProfileUpsert().status is None


class TestApplicationCreate:
    def test_default_status(self):
        assert ApplicationCreate(program_id=1).status == "saved"

    def test_arbitrary_status_is_rejected(self):
        with pytest.raises(ValidationError):
            ApplicationCreate(program_id=1, status="почти_подал")
