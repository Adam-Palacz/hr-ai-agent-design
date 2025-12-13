"""Test OpenAI API connection and model availability."""
import sys
import argparse
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    from langchain_openai import ChatOpenAI
except ImportError:
    try:
        from langchain.chat_models import ChatOpenAI
    except ImportError:
        from langchain_community.chat_models import ChatOpenAI

from config import settings
from core.logger import logger, setup_logger


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_success(message: str):
    """Print success message."""
    print(f"{Colors.GREEN}✅ {message}{Colors.RESET}")


def print_error(message: str):
    """Print error message."""
    print(f"{Colors.RED}❌ {message}{Colors.RESET}")


def print_warning(message: str):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠️  {message}{Colors.RESET}")


def print_info(message: str):
    """Print info message."""
    print(f"{Colors.BLUE}ℹ️  {message}{Colors.RESET}")


def print_header(message: str):
    """Print header message."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{message}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 80}{Colors.RESET}\n")


def test_api_key() -> tuple[bool, Optional[str]]:
    """Test if API key is available."""
    print_header("Testing API Key")
    
    try:
        api_key = settings.api_key
        if api_key:
            # Mask API key for display
            masked_key = f"{api_key[:7]}...{api_key[-4:]}" if len(api_key) > 11 else "***"
            print_success(f"API Key found: {masked_key}")
            return True, api_key
        else:
            print_error("API Key not found")
            return False, None
    except ValueError as e:
        print_error(f"API Key error: {str(e)}")
        return False, None


def test_text_model(api_key: str, model_name: str = None) -> Dict[str, Any]:
    """Test connection to text model."""
    print_header(f"Testing Text Model: {model_name or settings.openai_model}")
    
    result = {
        "success": False,
        "model_name": model_name or settings.openai_model,
        "response_time": None,
        "error": None,
        "response": None
    }
    
    try:
        # Initialize model
        model = model_name or settings.openai_model
        print_info(f"Initializing model: {model}")
        
        llm_kwargs = {
            "model": model,
            "temperature": 0.0,
            "timeout": 30,
            "max_retries": 1,
        }
        if api_key:
            llm_kwargs["openai_api_key"] = api_key
        
        llm = ChatOpenAI(**llm_kwargs)
        
        # Test with simple prompt
        test_prompt = "Say 'Hello' in one word."
        print_info(f"Sending test prompt: '{test_prompt}'")
        
        start_time = datetime.now()
        response = llm.invoke(test_prompt)
        end_time = datetime.now()
        
        response_time = (end_time - start_time).total_seconds()
        result["response_time"] = response_time
        
        # Extract response content
        if hasattr(response, 'content'):
            response_text = response.content
        else:
            response_text = str(response)
        
        result["response"] = response_text
        result["success"] = True
        
        print_success(f"Model responded in {response_time:.2f}s")
        print_info(f"Response: {response_text}")
        
    except Exception as e:
        result["error"] = str(e)
        print_error(f"Model test failed: {str(e)}")
        
        # Provide helpful error messages
        if "api key" in str(e).lower() or "authentication" in str(e).lower():
            print_warning("Check your API key in .env file or environment variables")
        elif "rate limit" in str(e).lower():
            print_warning("Rate limit exceeded. Wait a moment and try again.")
        elif "timeout" in str(e).lower():
            print_warning("Request timed out. Check your internet connection.")
        elif "model" in str(e).lower() and "not found" in str(e).lower():
            print_warning(f"Model '{model}' may not be available. Check model name.")
    
    return result


def test_vision_model(api_key: str, model_name: str = None) -> Dict[str, Any]:
    """Test connection to vision model."""
    vision_model = model_name or settings.openai_vision_model
    print_header(f"Testing Vision Model: {vision_model}")
    
    result = {
        "success": False,
        "model_name": vision_model,
        "response_time": None,
        "error": None,
        "response": None
    }
    
    # Check if model supports vision
    vision_models = ["gpt-4o", "gpt-4-vision-preview", "gpt-4-turbo"]
    if not any(vm in vision_model.lower() for vm in vision_models):
        print_warning(f"Model '{vision_model}' may not support vision. Skipping vision test.")
        result["error"] = "Model does not support vision"
        return result
    
    try:
        print_info(f"Initializing vision model: {vision_model}")
        
        llm_kwargs = {
            "model": vision_model,
            "temperature": 0.0,
            "timeout": 30,
            "max_retries": 1,
        }
        if api_key:
            llm_kwargs["openai_api_key"] = api_key
        
        llm = ChatOpenAI(**llm_kwargs)
        
        # Test with simple text prompt (vision models can handle text too)
        test_prompt = "Say 'Vision model working' in one sentence."
        print_info(f"Sending test prompt: '{test_prompt}'")
        
        start_time = datetime.now()
        response = llm.invoke(test_prompt)
        end_time = datetime.now()
        
        response_time = (end_time - start_time).total_seconds()
        result["response_time"] = response_time
        
        # Extract response content
        if hasattr(response, 'content'):
            response_text = response.content
        else:
            response_text = str(response)
        
        result["response"] = response_text
        result["success"] = True
        
        print_success(f"Vision model responded in {response_time:.2f}s")
        print_info(f"Response: {response_text}")
        
    except Exception as e:
        result["error"] = str(e)
        print_error(f"Vision model test failed: {str(e)}")
        
        if "api key" in str(e).lower():
            print_warning("Check your API key")
        elif "rate limit" in str(e).lower():
            print_warning("Rate limit exceeded")
        elif "model" in str(e).lower() and "not found" in str(e).lower():
            print_warning(f"Vision model '{vision_model}' may not be available")
    
    return result


def print_summary(results: Dict[str, Any]):
    """Print test summary."""
    print_header("Test Summary")
    
    api_key_ok = results["api_key"]["success"]
    text_model_ok = results["text_model"]["success"]
    vision_model_ok = results["vision_model"]["success"]
    vision_skipped = results["vision_model"].get("error") == "Skipped by user"
    
    print(f"{Colors.BOLD}API Key:{Colors.RESET} ", end="")
    if api_key_ok:
        print_success("OK")
    else:
        print_error("FAILED")
    
    print(f"{Colors.BOLD}Text Model ({results['text_model']['model_name']}):{Colors.RESET} ", end="")
    if text_model_ok:
        response_time = results["text_model"]["response_time"]
        print_success(f"OK ({response_time:.2f}s)")
    else:
        print_error(f"FAILED - {results['text_model']['error']}")
    
    print(f"{Colors.BOLD}Vision Model ({results['vision_model']['model_name']}):{Colors.RESET} ", end="")
    if vision_skipped:
        print_warning("SKIPPED")
    elif vision_model_ok:
        response_time = results["vision_model"]["response_time"]
        print_success(f"OK ({response_time:.2f}s)")
    else:
        error = results["vision_model"]["error"]
        if error == "Model does not support vision":
            print_warning("SKIPPED (model doesn't support vision)")
        else:
            print_error(f"FAILED - {error}")
    
    # Overall status
    print(f"\n{Colors.BOLD}Overall Status:{Colors.RESET} ", end="")
    if api_key_ok and text_model_ok:
        print_success("All critical tests passed! ✅")
        return 0
    else:
        print_error("Some tests failed! ❌")
        return 1


def test_models_list(api_key: str, models: List[str]) -> Dict[str, Dict[str, Any]]:
    """Test multiple models."""
    print_header(f"Testing {len(models)} Model(s)")
    
    results = {}
    for model in models:
        print(f"\n{Colors.BOLD}Testing model: {model}{Colors.RESET}")
        result = test_text_model(api_key, model_name=model)
        results[model] = result
    
    return results


def print_models_summary(results: Dict[str, Dict[str, Any]]):
    """Print summary for multiple models."""
    print_header("Models Test Summary")
    
    success_count = 0
    total_count = len(results)
    
    for model_name, result in results.items():
        print(f"{Colors.BOLD}{model_name}:{Colors.RESET} ", end="")
        if result["success"]:
            response_time = result["response_time"]
            print_success(f"OK ({response_time:.2f}s)")
            success_count += 1
        else:
            print_error(f"FAILED - {result['error']}")
    
    print(f"\n{Colors.BOLD}Overall:{Colors.RESET} {success_count}/{total_count} models passed")
    
    if success_count == total_count:
        print_success("All models working! ✅")
        return 0
    else:
        print_error("Some models failed! ❌")
        return 1


def main():
    """Run OpenAI connection tests."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(
        description="Test OpenAI API connection and model availability",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Test default models from settings
  python test_openai_connection.py
  
  # Test specific model
  python test_openai_connection.py --model gpt-4o
  
  # Test multiple models
  python test_openai_connection.py --models gpt-3.5-turbo gpt-4o gpt-4-turbo
  
  # Test model with custom name
  python test_openai_connection.py --model gpt-4o --name "My Custom Model"
        """
    )
    
    parser.add_argument(
        "--model",
        type=str,
        help="Test a specific model (e.g., gpt-4o, gpt-3.5-turbo)"
    )
    
    parser.add_argument(
        "--models",
        nargs="+",
        help="Test multiple models (e.g., --models gpt-3.5-turbo gpt-4o gpt-4-turbo)"
    )
    
    parser.add_argument(
        "--skip-vision",
        action="store_true",
        help="Skip vision model test when using default models"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logger(log_level=settings.log_level)
    
    # Test API key first
    api_key_ok, api_key = test_api_key()
    
    if not api_key_ok:
        print_error("\nCannot proceed without API key!")
        print_info("Please set OPENAI_API_KEY in .env file or environment variable")
        return 1
    
    # Handle different test modes
    if args.models:
        # Test multiple models
        models = args.models
        print_header("OpenAI Connection Test - Multiple Models")
        print_info(f"Testing {len(models)} model(s): {', '.join(models)}")
        print()
        
        results = test_models_list(api_key, models)
        exit_code = print_models_summary(results)
        
    elif args.model:
        # Test single specific model
        print_header("OpenAI Connection Test - Single Model")
        print_info(f"Testing model: {args.model}")
        print()
        
        result = test_text_model(api_key, model_name=args.model)
        
        print_header("Test Summary")
        if result["success"]:
            print_success(f"Model '{args.model}' is working! ✅")
            print_info(f"Response time: {result['response_time']:.2f}s")
            exit_code = 0
        else:
            print_error(f"Model '{args.model}' failed! ❌")
            print_error(f"Error: {result['error']}")
            exit_code = 1
    
    else:
        # Default: test models from settings
        print_header("OpenAI Connection Test")
        print_info(f"Testing connection to OpenAI models")
        print_info(f"Text Model: {settings.openai_model}")
        if not args.skip_vision:
            print_info(f"Vision Model: {settings.openai_vision_model}")
        print()
        
        results = {
            "api_key": {"success": True},
            "text_model": {"success": False},
            "vision_model": {"success": False}
        }
        
        # Test text model
        results["text_model"] = test_text_model(api_key)
        
        # Test vision model (unless skipped)
        if not args.skip_vision:
            results["vision_model"] = test_vision_model(api_key)
        else:
            results["vision_model"] = {
                "success": False,
                "model_name": settings.openai_vision_model,
                "error": "Skipped by user",
                "response_time": None,
                "response": None
            }
        
        # Print summary
        exit_code = print_summary(results)
    
    return exit_code


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print_error("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        print_error(f"\n\nUnexpected error: {str(e)}")
        logger.exception("Unexpected error in test")
        sys.exit(1)

