import pytest
import time
import json
from playwright.sync_api import Page, expect

def close_banner_if_present(page: Page):
    try:
        # Check for banner close button with a short timeout
        close_banner = page.locator(".pi-times, button[aria-label='Close'], .close-btn").first
        if close_banner.is_visible(timeout=2000):
            close_banner.click()
    except:
        pass

def wait_for_comfyui_load(page: Page):
    # .comfy-menu or .comfyui-menu or .side-bar-button should be attached
    page.wait_for_selector(".comfy-menu, .comfyui-menu, .side-bar-button", state="attached", timeout=45000)
    # Ensure blocking overlays are gone
    page.wait_for_selector("#comfy-file-input-overlay", state="hidden", timeout=10000)
    page.wait_for_selector(".comfy-modal-content", state="hidden", timeout=5000)

def open_settings(page: Page):
    """
    Robustly open the settings modal.
    Retries with multiple strategies (Icon, Shortcut, Fallback).
    """
    clicked = False
    
    # Strategy 1: Precise selector (icon-[lucide--settings] or aria-label)
    # Wait for the button to be ready. ComfyUI loading can be slow.
    try:
        settings_btn_selector = "button:has(i[class*='icon-[lucide--settings]']), button[aria-label*='Ctrl + ,']"
        # Wait up to 10s for the button to appear
        page.wait_for_selector(settings_btn_selector, state="visible", timeout=10000)
        
        settings_btn = page.locator(settings_btn_selector).first
        if settings_btn.is_visible():
            print("DEBUG: Found settings button by icon/aria-label")
            settings_btn.click(force=True)
            clicked = True
    except Exception as e:
        print(f"DEBUG: Strategy 1 search failed: {e}")

    # Strategy 2: Keyboard Shortcut (Ctrl+,)
    if not clicked:
        try:
             print("DEBUG: Trying strategy 2 (Shortcut Ctrl+,)...")
             page.keyboard.press("Control+,")
             clicked = True
        except Exception as e:
             print(f"DEBUG: Strategy 2 failed: {e}")

    # Verify modal opened
    try:
        # Wait for modal dialog to be strictly visible
        page.wait_for_selector("div[role='dialog']:visible, .p-dialog:visible, .comfy-modal:visible", state="visible", timeout=10000)
        print("DEBUG: Settings modal opened.")
    except Exception as e:
        print("DEBUG: Settings modal did not appear after interaction.")
        page.screenshot(path="e2e_failure_open_settings.png")
        raise e

# @pytest.mark.skip(reason="Fixed UI selectors based on analysis")
def test_settings_workflow(page: Page, comfyui_server):
    # 1. ComfyUIにアクセスしてロードを待機
    page.set_viewport_size({"width": 1920, "height": 1080})
    page.goto(comfyui_server)
    
    wait_for_comfyui_load(page)
    close_banner_if_present(page)

    # 2. 設定を開く
    open_settings(page)
    
    # 3. 初期状態を確認
    # モーダル内のサイドメニューに 'comfyui_remove_print' があるか確認し、クリックして選択
    try:
         category_btn = page.locator("text=comfyui_remove_print")
         category_btn.wait_for(state="visible", timeout=5000)
         category_btn.click()
    except Exception:
         print("DEBUG: 'comfyui_remove_print' text not found in modal.")
         page.screenshot(path="e2e_settings_modal_content.png")
         try:
             # Dump visible text in modal
             print(f"DEBUG: Modal text: {page.locator('.p-dialog:visible').inner_text()}")
         except:
             pass
         raise
    
    # モーダルの項目が表示されるまで待つ
    # 言語によって "Edit Hook Settings" (EN) または "フック設定を編集" (JA)
    # テキストが見つからない場合があるため、"編集..." ボタンの存在で確認する
    try:
        page.wait_for_selector("button:has-text('Edit...'), button:has-text('編集...')", state="visible", timeout=5000)
    except Exception as e:
        print("DEBUG: Setting 'Edit' button not found.")
        page.screenshot(path="e2e_failure_setting_item.png")
        raise e

    # 4. 言語を日本語に切り替える (UI操作ベース)
    # ComfyUI V1系/ポータブル版での確実な言語切り替え
    page.evaluate("() => { const app = window.comfyAPI?.app?.app || window.app; if(app) { app.ui.settings.setSettingValue('Comfy.Locale', 'ja'); location.reload(); } }")
    
    # リロード待ち
    wait_for_comfyui_load(page)
    close_banner_if_present(page)

    # 5. 日本語に切り替わったことを再確認
    open_settings(page)
    
    # カテゴリを選択
    page.locator("text=comfyui_remove_print").click()
    
    # フック設定を編集 (ja/main.json より)
    # wait_for_selector is more reliable than expect().to_be_visible() for finding steps
    page.wait_for_selector("text=フック設定を編集", timeout=5000)
    expect(page.get_by_text("フック設定を編集")).to_be_visible()
    
    # 6. 「編集...」ボタンをクリックしてモーダルを開く
    page.get_by_role("button", name="編集...").click()
    
    # 7. モーダルのタイトルを確認
    expect(page.get_by_text("Remove Print 設定")).to_be_visible()
    
    # 8. フックを追加
    modal = page.locator("#remove-print-modal")
    modal.get_by_placeholder("ノード名").fill("CheckpointLoaderSimple")
    modal.get_by_placeholder("メソッド名").fill("load_checkpoint")
    modal.get_by_role("button", name="追加").click()
    
    # 9. リストに追加されたことを確認
    expect(modal.get_by_text("CheckpointLoaderSimple.load_checkpoint")).to_be_visible()
    
    # 10. 保存
    modal.get_by_role("button", name="保存して適用").click()
    # Toast or status message
    expect(modal.get_by_text("保存して適用しました")).to_be_visible()
    
    # 11. 閉じる
    modal.get_by_text("✕").click()

def test_reset_functionality(page: Page, comfyui_server):
    page.set_viewport_size({"width": 1920, "height": 1080})
    page.goto(comfyui_server)
    wait_for_comfyui_load(page)
    
    # 言語を日本語にする（リロードなしで試みる）
    page.evaluate("() => { const app = window.comfyAPI?.app?.app || window.app; if(app) { app.ui.settings.setSettingValue('Comfy.Locale', 'ja'); } }")
    # Setting value change might take a tick to propagate
    
    open_settings(page)
    
    # カテゴリを選択
    page.locator("text=comfyui_remove_print").click()
    
    # 日本語のボタンが表示されるのを待つ
    btn = page.get_by_role("button", name="編集...").or_(page.get_by_role("button", name="Edit..."))
    btn.first.click()
    
    modal = page.locator("#remove-print-modal")
    
    # Handle dialog (OK/Cancel) specifically for the reset action if it uses window.confirm logic
    # But here it seems to be using custom modal logic or page.once("dialog") handles browser native confirm/alert
    page.once("dialog", lambda dialog: dialog.accept())
    
    # ボタン名も複数対応
    reset_btn = modal.get_by_role("button", name="リセット").or_(modal.get_by_role("button", name="Reset"))
    reset_btn.first.click()
    
    expect(modal.get_by_text("デフォルト設定に戻しました").or_(modal.get_by_text("Reset to defaults"))).to_be_visible()
