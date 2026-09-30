// Registers a "VideoRouter" section in ComfyUI's own Settings dialog (gear icon) with one
// text field for the API key — confirmed API against docs.comfy.org/custom-nodes/js/
// javascript_settings, 2026-09-14. Saving here calls ComfyUI's existing generic
// `POST /settings/{id}` route (app/app_settings.py), which persists to
// `user/default/comfy.settings.json` server-side — NOT into workflow.json, so it isn't
// exposed if a user shares a workflow file (unlike the per-node `api_key` widget, which
// stays as a lower-precedence manual override — see util/client.py's `resolve_api_key`).
// No `LLMROUTER_API_KEY` environment-variable fallback (removed 2026-09-14) — Settings or
// the per-node widget, one clear source of truth, not several silently-stacked ones.
//
// No masked/password input type exists in ComfyUI's settings schema as of this writing
// (confirmed: the full `type` list is boolean/text/number/slider/combo/color/image/hidden,
// no password/secret variant) — the fork's `SettingItem.vue` override for this specific
// setting id gates it behind an explicit "Edit" click and masks the display instead
// (`comfyui_frontend_fork`'s patch, not something this JS file itself controls).
import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "videorouter.settings",
    settings: [
        {
            id: "VideoRouter.ApiKey",
            name: "API Key",
            // Tried filing this under `category: ["User", ...]` to merge into ComfyUI's
            // built-in "User" panel — live-tested 2026-09-14, does NOT merge. ComfyUI's
            // core category panels (User/Comfy/LiteGraph/Appearance/...) are hardcoded,
            // not assembled from generic registered settings — using their exact name here
            // just creates a SECOND, unrelated "User" entry under "Other" (confirmed via
            // screenshot: a plug-icon "User" row appears alongside the real person-icon
            // one). Reverted to a dedicated "VideoRouter" category — "Other" is genuinely
            // the correct/only place a third-party setting can land, not a workaround.
            category: ["VideoRouter", "Auth", "API Key"],
            type: "text",
            defaultValue: "",
            tooltip: "Your videorouter.sh key (llmr_sk_...). Get one at "
                    + "https://videorouter.sh/keys.",
        },
    ],
});
