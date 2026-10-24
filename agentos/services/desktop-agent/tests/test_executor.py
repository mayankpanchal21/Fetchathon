import pytest
from pathlib import Path
from app.config import settings
from app.executor import (
    get_screen_info,
    take_screenshot,
    create_directory,
    write_text_file,
    read_text_file,
    list_files,
    search_files,
    run_approved_command,
    browser_manager
)


def test_get_screen_info():
    info = get_screen_info()
    assert "width" in info
    assert "height" in info
    assert info["width"] > 0
    assert info["height"] > 0
    assert "operating_system" in info


def test_take_screenshot(tmp_path):
    res = take_screenshot()
    assert "saved_path" in res
    assert Path(res["saved_path"]).exists()
    assert res["width"] > 0
    assert res["height"] > 0
    assert res["base64_preview"].startswith("data:image/jpeg;base64,")


def test_filesystem_operations(tmp_path):
    orig = settings.allowed_workspace
    try:
        settings.allowed_workspace = tmp_path
        # 1. Create directory
        res_dir = create_directory("test_folder")
        assert res_dir["status"] == "success"
        assert (tmp_path / "test_folder").is_dir()

        # 2. Write file
        res_write = write_text_file("test_folder/sample.txt", "Hello AgentOS Hackathon!")
        assert res_write["status"] == "success"
        assert res_write["bytes_written"] > 0

        # 3. Read file
        res_read = read_text_file("test_folder/sample.txt")
        assert res_read["content"] == "Hello AgentOS Hackathon!"

        # 4. List files
        res_list = list_files("test_folder")
        assert res_list["total_items"] == 1
        assert res_list["items"][0]["name"] == "sample.txt"

        # 5. Search files
        res_search = search_files(".", query="sample")
        assert res_search["total_matches"] == 1
    finally:
        settings.allowed_workspace = orig


def test_terminal_approved_command():
    # Test valid command template
    res = run_approved_command("git_status")
    assert "exit_code" in res
    assert "stdout" in res

    # Unknown command should fail
    from app.policy import PolicyViolation
    with pytest.raises(PolicyViolation):
        run_approved_command("bash_exec", {"cmd": "echo test"})


@pytest.mark.asyncio
async def test_playwright_browser_navigation():
    # Navigate to lightweight example page
    try:
        res = await browser_manager.browser_navigate("https://example.com")
        assert res["verified"] is True
        assert "Example" in res["title"]

        content = await browser_manager.browser_get_page_content()
        assert "documentation examples" in content["text_sample"].lower()
    finally:
        await browser_manager.close()
