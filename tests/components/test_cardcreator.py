import pytest
from healthchain.pipeline.components.cdscardcreator import CdsCardCreator
from healthchain.io.containers import Document
from healthchain.models.responses.cdsresponse import Card, Source, IndicatorEnum


def test_default_template_rendering(basic_creator):
    content = "Test message"
    card = basic_creator.create_card(content)

    assert isinstance(card, Card)
    assert card.summary == "Test message"[:140]
    assert card.indicator == IndicatorEnum.info
    assert card.source == Source(label="Card Generated by HealthChain")
    assert card.detail == "Test message"


def test_custom_template_rendering(custom_template_creator):
    content = "Test message"
    card = custom_template_creator.create_card(content)

    assert card.summary == "Custom: Test message"
    assert card.indicator == IndicatorEnum.warning
    assert card.source == Source(label="Card Generated by HealthChain")
    assert card.detail == "Test message"


def test_long_summary_truncation(basic_creator):
    long_content = "x" * 200
    card = basic_creator.create_card(long_content)

    assert len(card.summary) == 140
    assert card.summary == "x" * 140


def test_invalid_template_json(basic_creator):
    invalid_template = """
    {
        "summary": {{ invalid_json }},
    }
    """
    with pytest.raises(ValueError):
        creator = CdsCardCreator(template=invalid_template)
        creator(Document(data="test"))


def test_document_processing_with_model_output():
    creator = CdsCardCreator(source="huggingface", task="summarization")
    doc = Document(data="test")
    doc.models.add_output(
        "huggingface", "summarization", [{"summary_text": "Model summary"}]
    )

    processed_doc = creator(doc)
    cards = processed_doc.cds.get_cards()

    assert len(cards) == 1
    assert cards[0].summary == "Model summary"
    assert cards[0].indicator == IndicatorEnum.info


def test_document_processing_with_static_content():
    creator = CdsCardCreator(static_content="Static content")
    doc = Document(data="test")

    processed_doc = creator(doc)
    cards = processed_doc.cds.get_cards()

    assert len(cards) == 1
    assert cards[0].summary == "Static content"


def test_missing_model_output_warning(caplog):
    creator = CdsCardCreator(source="huggingface", task="missing_task")
    doc = Document(data="test")

    processed_doc = creator(doc)

    assert "No generated text for huggingface/missing_task found" in caplog.text
    assert not processed_doc.cds.get_cards()


def test_invalid_input_configuration():
    creator = CdsCardCreator()  # No content or source/task specified
    doc = Document(data="test")

    with pytest.raises(ValueError) as exc_info:
        creator(doc)

    assert (
        "Either model output (source and task) or content need to be provided"
        in str(exc_info.value)
    )


def test_template_file_loading(tmp_path):
    # Create a temporary template file
    template_file = tmp_path / "test_template.json"
    template_content = """
    {
        "summary": "File Template: {{ model_output }}",
        "indicator": "warning",
        "source": {{ default_source | tojson }},
        "detail": "{{ model_output }}"
    }
    """
    template_file.write_text(template_content)

    creator = CdsCardCreator(template_path=template_file)
    card = creator.create_card("Test message")

    assert card.summary == "File Template: Test message"
    assert card.indicator == IndicatorEnum.warning
    assert card.source == Source(label="Card Generated by HealthChain")
    assert card.detail == "Test message"


def test_nonexistent_template_file(caplog):
    creator = CdsCardCreator(template_path="nonexistent_template.json")
    card = creator.create_card("Test message")
    assert card.summary == "Test message"
    assert card.indicator == IndicatorEnum.info
    assert card.source == Source(label="Card Generated by HealthChain")
    assert card.detail == "Test message"
    assert "Error loading template" in caplog.text


def test_invalid_template_file(tmp_path):
    # Create a temporary template file with invalid JSON
    template_file = tmp_path / "invalid_template.json"
    template_content = """
    {
        "summary": {{ invalid_json }},
        "indicator": "warning"
    """  # Invalid JSON
    template_file.write_text(template_content)

    with pytest.raises(ValueError):
        creator = CdsCardCreator(template_path=template_file)
        creator.create_card("Test message")
