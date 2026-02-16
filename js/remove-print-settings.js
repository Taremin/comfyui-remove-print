import { app } from "../../scripts/app.js";

const EXTENSION_NAME = "comfyui-remove-print";

/** @type {Record<string, Record<string, string>>} */
let MESSAGES = { en: {}, ja: {} };

/**
 * 翻訳を取得するヘルパー関数
 * @param {string} key 
 * @param {Record<string, any>} [params] 
 * @returns {string}
 */
function t(key, params = {}) {
    const locale = app.ui.settings.getSettingValue("Comfy.Locale") || "en";
    const dict = MESSAGES[locale] || MESSAGES["en"];
    let text = dict[key] || MESSAGES["en"][key] || key;

    for (const [k, v] of Object.entries(params)) {
        text = text.replace(`{${k}}`, v);
    }
    return text;
}

/**
 * 翻訳データをロードする
 */
async function loadTranslations() {
    try {
        const [enResp, jaResp] = await Promise.all([
            fetch("/remove-print/locales/en"),
            fetch("/remove-print/locales/ja")
        ]);

        MESSAGES.en = await enResp.json();
        MESSAGES.ja = await jaResp.json();
    } catch (e) {
        console.error(`[${EXTENSION_NAME}] Failed to load translations:`, e);
    }
}

/**
 * フック設定を読み込む
 * ユーザー設定が存在すればそれを、なければデフォルト設定を返す
 */
async function loadHooks() {
    try {
        const resp = await fetch("/remove-print/hooks");
        if (resp.ok) {
            const data = await resp.json();
            return { hooks: data.hooks || [] };
        }
    } catch (e) {
        console.error(`[${t("modal.title")}] Failed to load settings:`, e);
    }

    return { hooks: [] };
}

/**
 * フック設定をユーザーデータとして保存
 */
async function saveHooks(hooks) {
    const body = JSON.stringify({ hooks }, null, 2);
    const resp = await fetch("/remove-print/hooks", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: body,
    });
    if (!resp.ok) {
        throw new Error(`${t("modal.saveError", { message: resp.status })}`);
    }
    return resp.json();
}

/**
 * ユーザー設定を削除してデフォルトに戻す
 */
async function resetToDefault() {
    const resp = await fetch("/remove-print/hooks", {
        method: "DELETE",
    });
    if (!resp.ok) {
        throw new Error(`${t("modal.resetError", { message: resp.status })}`);
    }
    return resp.json();
}



/**
 * モーダルダイアログを作成して表示
 */
function showSettingsDialog() {
    // 既存のモーダルがあれば削除
    const existing = document.getElementById("remove-print-modal");
    if (existing) existing.remove();

    // オーバーレイ
    const overlay = document.createElement("div");
    overlay.id = "remove-print-modal";
    overlay.style.cssText = `
    position: fixed; top: 0; left: 0; width: 100%; height: 100%;
    background: rgba(0,0,0,0.6); z-index: 10000;
    display: flex; align-items: center; justify-content: center;
  `;

    // モーダル本体
    const modal = document.createElement("div");
    modal.style.cssText = `
    background: #2a2a2a; color: #eee; border-radius: 12px;
    padding: 24px; min-width: 500px; max-width: 700px; max-height: 80vh;
    box-shadow: 0 8px 32px rgba(0,0,0,0.5); overflow-y: auto;
    font-family: system-ui, sans-serif;
  `;

    // ヘッダー
    const header = document.createElement("div");
    header.style.cssText = `
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 16px; border-bottom: 1px solid #444; padding-bottom: 12px;
  `;
    const title = document.createElement("h2");
    title.style.cssText = "margin: 0; font-size: 18px; color: #fff;";
    title.textContent = t("modal.title");
    header.appendChild(title);

    const closeBtn = document.createElement("button");
    closeBtn.textContent = "✕";
    closeBtn.style.cssText = `
    background: none; border: none; color: #aaa; font-size: 20px;
    cursor: pointer; padding: 4px 8px;
  `;
    closeBtn.onclick = () => overlay.remove();
    header.appendChild(closeBtn);

    // 注意メッセージ
    const notice = document.createElement("div");
    notice.style.cssText = `
    background: #3a3520; border: 1px solid #665a22; border-radius: 8px;
    padding: 10px 14px; margin-bottom: 16px; font-size: 13px; color: #e8d44d;
  `;
    notice.textContent = t("modal.notice");

    // フックリストコンテナ
    const listContainer = document.createElement("div");
    listContainer.id = "remove-print-hook-list";

    // 新規追加フォーム
    const addForm = document.createElement("div");
    addForm.style.cssText = `
    display: flex; gap: 8px; margin-top: 16px; align-items: center;
  `;

    // ノード入力 + datalist
    const nodeDatalist = document.createElement("datalist");
    nodeDatalist.id = "remove-print-node-list";

    const nodeInput = document.createElement("input");
    nodeInput.placeholder = t("modal.nodePlaceholder");
    nodeInput.setAttribute("list", "remove-print-node-list");
    nodeInput.style.cssText = `
    flex: 1; padding: 8px 12px; background: #333; border: 1px solid #555;
    border-radius: 6px; color: #eee; font-size: 14px;
  `;

    // メソッド入力 + datalist
    const methodDatalist = document.createElement("datalist");
    methodDatalist.id = "remove-print-method-list";

    const methodInput = document.createElement("input");
    methodInput.placeholder = t("modal.methodPlaceholder");
    methodInput.setAttribute("list", "remove-print-method-list");
    methodInput.style.cssText = nodeInput.style.cssText;

    const addBtn = document.createElement("button");
    addBtn.textContent = t("modal.addButton");
    addBtn.style.cssText = `
    padding: 8px 16px; background: #2d6a4f; border: none; border-radius: 6px;
    color: #fff; cursor: pointer; font-size: 14px; white-space: nowrap;
  `;

    addForm.appendChild(nodeInput);
    addForm.appendChild(nodeDatalist);
    addForm.appendChild(methodInput);
    addForm.appendChild(methodDatalist);
    addForm.appendChild(addBtn);

    // ノード一覧をAPIから取得してdatalistに設定
    fetch("/remove-print/nodes")
        .then((r) => r.json())
        .then(({ nodes }) => {
            nodeDatalist.innerHTML = "";
            nodes.forEach((name) => {
                const opt = document.createElement("option");
                opt.value = name;
                nodeDatalist.appendChild(opt);
            });
        })
        .catch(() => { });

    // ノード選択時にメソッド候補を動的取得
    let lastFetchedNode = "";
    nodeInput.addEventListener("change", fetchMethods);
    nodeInput.addEventListener("blur", fetchMethods);

    function fetchMethods() {
        const nodeName = nodeInput.value.trim();
        if (!nodeName || nodeName === lastFetchedNode) return;
        lastFetchedNode = nodeName;

        fetch(`/remove-print/methods/${encodeURIComponent(nodeName)}`)
            .then((r) => r.json())
            .then(({ methods }) => {
                methodDatalist.innerHTML = "";
                methods.forEach((name) => {
                    const opt = document.createElement("option");
                    opt.value = name;
                    methodDatalist.appendChild(opt);
                });
                // メソッド入力にフォーカスして候補を表示しやすくする
                methodInput.focus();
            })
            .catch(() => {
                methodDatalist.innerHTML = "";
            });
    }

    // フッターボタン
    const footer = document.createElement("div");
    footer.style.cssText = `
    display: flex; gap: 8px; margin-top: 20px; justify-content: flex-end;
    border-top: 1px solid #444; padding-top: 16px;
  `;

    const resetBtn = document.createElement("button");
    resetBtn.textContent = t("modal.resetButton");
    resetBtn.style.cssText = `
    padding: 8px 16px; background: #555; border: none; border-radius: 6px;
    color: #ddd; cursor: pointer; font-size: 14px;
  `;

    const saveBtn = document.createElement("button");
    saveBtn.textContent = t("modal.saveButton");
    saveBtn.style.cssText = `
    padding: 8px 20px; background: #1a73e8; border: none; border-radius: 6px;
    color: #fff; cursor: pointer; font-size: 14px; font-weight: bold;
  `;

    footer.appendChild(resetBtn);
    footer.appendChild(saveBtn);

    // 組み立て
    modal.appendChild(header);
    modal.appendChild(notice);
    modal.appendChild(listContainer);
    modal.appendChild(addForm);
    modal.appendChild(footer);
    overlay.appendChild(modal);
    document.body.appendChild(overlay);

    // オーバーレイクリックで閉じる
    overlay.addEventListener("click", (e) => {
        if (e.target === overlay) overlay.remove();
    });

    // --- データ管理 ---
    let currentHooks = [];

    function renderHookList() {
        listContainer.innerHTML = "";

        if (currentHooks.length === 0) {
            const empty = document.createElement("div");
            empty.style.cssText = `
        text-align: center; color: #888; padding: 24px; font-size: 14px;
      `;
            empty.textContent = t("modal.emptyMessage");
            listContainer.appendChild(empty);
            return;
        }

        currentHooks.forEach((hook, index) => {
            const item = document.createElement("div");
            item.style.cssText = `
        display: flex; align-items: center; gap: 10px; padding: 10px 12px;
        background: #333; border-radius: 8px; margin-bottom: 8px;
      `;

            // 有効/無効トグル
            const toggle = document.createElement("input");
            toggle.type = "checkbox";
            toggle.checked = hook.enabled !== false;
            toggle.style.cssText = `
        width: 18px; height: 18px; cursor: pointer; accent-color: #2d6a4f;
      `;
            toggle.onchange = () => {
                currentHooks[index].enabled = toggle.checked;
                label.style.color = toggle.checked ? "#eee" : "#888";
            };

            // ノード名.メソッド名
            const label = document.createElement("span");
            label.style.cssText = `
        flex: 1; font-family: monospace; font-size: 14px;
        color: ${hook.enabled !== false ? "#eee" : "#888"};
      `;
            label.textContent = `${hook.node}.${hook.method}`;

            // 削除ボタン
            const delBtn = document.createElement("button");
            delBtn.textContent = "🗑";
            delBtn.title = t("modal.deleteTooltip");
            delBtn.style.cssText = `
        background: none; border: none; color: #e74c3c; font-size: 16px;
        cursor: pointer; padding: 4px 8px; border-radius: 4px;
      `;
            delBtn.onmouseover = () => (delBtn.style.background = "#4a2020");
            delBtn.onmouseout = () => (delBtn.style.background = "none");
            delBtn.onclick = () => {
                currentHooks.splice(index, 1);
                renderHookList();
            };

            item.appendChild(toggle);
            item.appendChild(label);
            item.appendChild(delBtn);
            listContainer.appendChild(item);
        });
    }

    // 初期読み込み
    loadHooks().then(({ hooks }) => {
        currentHooks = hooks.map((h) => ({ ...h }));
        renderHookList();
    });

    // 追加ボタン
    addBtn.onclick = () => {
        const node = nodeInput.value.trim();
        const method = methodInput.value.trim();
        if (!node || !method) {
            alert(t("modal.inputRequired"));
            return;
        }

        // 重複チェック
        if (currentHooks.some((h) => h.node === node && h.method === method)) {
            alert(t("modal.duplicateHook"));
            return;
        }

        currentHooks.push({ node, method, enabled: true });
        nodeInput.value = "";
        methodInput.value = "";
        renderHookList();
    };

    // 保存ボタン
    saveBtn.onclick = async () => {
        saveBtn.disabled = true;
        saveBtn.textContent = t("modal.saving");
        try {
            const result = await saveHooks(currentHooks);
            notice.style.background = "#1a3a2a";
            notice.style.borderColor = "#2d6a4f";
            notice.style.color = "#5fe89d";
            notice.textContent = t("modal.saveSuccess", { count: result.hooked?.length || 0 });

            // 最新の設定で再表示
            const { hooks } = await loadHooks();
            currentHooks = hooks.map((h) => ({ ...h }));
            renderHookList();
        } catch (e) {
            notice.style.background = "#3a2020";
            notice.style.borderColor = "#cc4444";
            notice.style.color = "#e74c3c";
            notice.textContent = t("modal.saveError", { message: e.message });
        } finally {
            saveBtn.disabled = false;
            saveBtn.textContent = t("modal.saveButton");
        }
    };

    // リセットボタン
    resetBtn.onclick = async () => {
        if (!confirm(t("modal.confirmReset"))) return;
        resetBtn.disabled = true;
        resetBtn.textContent = t("modal.resetting");
        try {
            await resetToDefault();
            const { hooks } = await loadHooks();
            currentHooks = hooks.map((h) => ({ ...h }));
            renderHookList();

            notice.style.background = "#1a3a2a";
            notice.style.borderColor = "#2d6a4f";
            notice.style.color = "#5fe89d";
            notice.textContent = t("modal.resetSuccess");
        } catch (e) {
            notice.style.background = "#3a2020";
            notice.style.borderColor = "#cc4444";
            notice.style.color = "#e74c3c";
            notice.textContent = t("modal.resetError", { message: e.message });
        } finally {
            resetBtn.disabled = false;
            resetBtn.textContent = t("modal.resetButton");
        }
    };
}

// ComfyUIのSettingsパネルに設定項目を登録
app.registerExtension({
    name: `${EXTENSION_NAME}.settings`,
    async setup() {
        await loadTranslations();
        // Settings パネルに「Remove Print フック設定」エントリを追加
        app.ui.settings.addSetting({
            id: "ComfyuiRemovePrint.Hooks",
            get name() {
                return t("settings.hookName");
            },
            get category() {
                return ["comfyui_remove_print", t("settings.category")];
            },
            type: () => {
                const editBtn = document.createElement("button");
                editBtn.textContent = t("modal.editButton");
                editBtn.style.cssText = `
                    padding: 4px 12px; background: #1a73e8; border: none;
                    border-radius: 4px; color: #fff; cursor: pointer;
                    font-size: 13px;
                `;
                editBtn.onclick = async (e) => {
                    e.preventDefault();
                    await loadTranslations(); // Ensure translations are fresh
                    showSettingsDialog();
                };
                return editBtn;
            },
            defaultValue: "",
        });
    },
});
