from backend.app.models.schemas import TakeoffOutput
def test_takeoff_output_validates():
    data = {"project_id": "P1","items":[{"assembly_id":"03-300","measure_type":"LF","qty":10,"unit":"LF","confidence":0.9,"evidence_uri":"/snips/A1/1.png","sheet_id":"A1"}]}
    out = TakeoffOutput(**data)
    assert out.items[0].confidence <= 1
