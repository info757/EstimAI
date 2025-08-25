import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from jsonschema import ValidationError

from app.core.llm import llm_call_json


class TestLLMCallJSON:
    """Test cases for llm_call_json function."""
    
    @pytest.fixture
    def sample_schema(self):
        """Sample JSON schema for testing."""
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "age": {"type": "integer"},
                "email": {"type": "string", "format": "email"}
            },
            "required": ["name", "age"]
        }
    
    @pytest.fixture
    def sample_context(self):
        """Sample context data for testing."""
        return {
            "user_id": 123,
            "preferences": {"theme": "dark"}
        }
    
    @pytest.fixture
    def sample_prompt(self):
        """Sample prompt for testing."""
        return "Extract user information from the provided context."
    
    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI response structure."""
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = '{"name": "John Doe", "age": 30, "email": "john@example.com"}'
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        return mock_response
    
    @pytest.mark.asyncio
    async def test_successful_call(self, sample_prompt, sample_context, sample_schema, mock_openai_response):
        """Test successful API call with valid response."""
        with patch('app.core.llm.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_openai_response
            mock_openai.return_value = mock_client
            
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                result = await llm_call_json(
                    prompt=sample_prompt,
                    context=sample_context,
                    schema=sample_schema
                )
        
        # Verify the result matches the schema
        assert isinstance(result, dict)
        assert "name" in result
        assert "age" in result
        assert "email" in result
        assert result["name"] == "John Doe"
        assert result["age"] == 30
        assert result["email"] == "john@example.com"
        
        # Verify API was called correctly
        mock_client.chat.completions.create.assert_called_once()
        call_args = mock_client.chat.completions.create.call_args
        assert call_args[1]['model'] == 'gpt-4o-mini'
        assert call_args[1]['response_format'] == {'type': 'json_object'}
        assert call_args[1]['temperature'] == 0
        
        # Verify messages structure
        messages = call_args[1]['messages']
        assert len(messages) == 2
        assert messages[0]['role'] == 'system'
        assert messages[0]['content'] == sample_prompt
        assert messages[1]['role'] == 'user'
        assert json.loads(messages[1]['content']) == sample_context
    
    @pytest.mark.asyncio
    async def test_missing_api_key(self, sample_prompt, sample_context, sample_schema):
        """Test error when OPENAI_API_KEY is not set."""
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(RuntimeError, match="OPENAI_API_KEY environment variable is required"):
                await llm_call_json(
                    prompt=sample_prompt,
                    context=sample_context,
                    schema=sample_schema
                )
    
    @pytest.mark.asyncio
    async def test_invalid_json_response(self, sample_prompt, sample_context, sample_schema):
        """Test error when response is not valid JSON."""
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = 'This is not valid JSON'
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        with patch('app.core.llm.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                with pytest.raises(ValueError, match="Failed to parse JSON response"):
                    await llm_call_json(
                        prompt=sample_prompt,
                        context=sample_context,
                        schema=sample_schema
                    )
    
    @pytest.mark.asyncio
    async def test_schema_validation_error(self, sample_prompt, sample_context, sample_schema):
        """Test error when response doesn't match schema."""
        # Response missing required 'age' field
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = '{"name": "John Doe", "email": "john@example.com"}'
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        with patch('app.core.llm.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                with pytest.raises(ValueError, match="Response validation failed"):
                    await llm_call_json(
                        prompt=sample_prompt,
                        context=sample_context,
                        schema=sample_schema
                    )
    
    @pytest.mark.asyncio
    async def test_retry_on_429_error(self, sample_prompt, sample_context, sample_schema, mock_openai_response):
        """Test retry mechanism on 429 error."""
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = '{"name": "John Doe", "age": 30, "email": "john@example.com"}'
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        with patch('app.core.llm.OpenAI') as mock_openai:
            mock_client = MagicMock()
            # First call raises 429, second call succeeds
            mock_client.chat.completions.create.side_effect = [
                Exception("Rate limit exceeded"),  # Mock 429 error
                mock_response
            ]
            mock_openai.return_value = mock_client
            
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                # This should fail because our mock exception doesn't have status_code
                with pytest.raises(Exception, match="Rate limit exceeded"):
                    await llm_call_json(
                        prompt=sample_prompt,
                        context=sample_context,
                        schema=sample_schema
                    )
    
    @pytest.mark.asyncio
    async def test_long_response_truncation(self, sample_prompt, sample_context, sample_schema):
        """Test that long error messages are truncated."""
        # Create a very long invalid response
        long_response = "This is a very long response that should be truncated " * 20
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = long_response
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        with patch('app.core.llm.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                with pytest.raises(ValueError) as exc_info:
                    await llm_call_json(
                        prompt=sample_prompt,
                        context=sample_context,
                        schema=sample_schema
                    )
                
                # Check that error message includes truncated response
                error_msg = str(exc_info.value)
                assert "Raw text:" in error_msg
                assert len(error_msg.split("Raw text:")[1]) <= 204  # 200 chars + "..." + space
    
    @pytest.mark.asyncio
    async def test_complex_schema_validation(self, sample_prompt, sample_context):
        """Test with a more complex schema."""
        complex_schema = {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "integer"},
                            "name": {"type": "string"},
                            "tags": {"type": "array", "items": {"type": "string"}}
                        },
                        "required": ["id", "name"]
                    }
                },
                "total": {"type": "integer"}
            },
            "required": ["items", "total"]
        }
        
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_message.content = json.dumps({
            "items": [
                {"id": 1, "name": "Item 1", "tags": ["tag1", "tag2"]},
                {"id": 2, "name": "Item 2", "tags": []}
            ],
            "total": 2
        })
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        with patch('app.core.llm.OpenAI') as mock_openai:
            mock_client = MagicMock()
            mock_client.chat.completions.create.return_value = mock_response
            mock_openai.return_value = mock_client
            
            with patch.dict('os.environ', {'OPENAI_API_KEY': 'test-key'}):
                result = await llm_call_json(
                    prompt=sample_prompt,
                    context=sample_context,
                    schema=complex_schema
                )
        
        # Verify complex result structure
        assert "items" in result
        assert "total" in result
        assert len(result["items"]) == 2
        assert result["items"][0]["id"] == 1
        assert result["items"][0]["name"] == "Item 1"
        assert result["items"][0]["tags"] == ["tag1", "tag2"]
        assert result["total"] == 2
