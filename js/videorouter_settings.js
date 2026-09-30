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
        {
            // Applies to EVERY relayed Partner Node request (Kling/MiniMax/Veo/Meshy/...)
            // — a single global preference, not a per-node widget, since none of the
            // official nodes this pack relays have any host-selection input of their own to
            // hang a per-instance control on (`gateway/comfy_proxy.py`'s own docstring: the
            // official node schemas are owned by Comfy-Org, not this pack). Read server-side
            // at import time by `comfy_relay.py::install()` (same settings-file-on-disk
            // mechanism as the API key above) and threaded through on every proxied request
            // as `POST /v1/videos|images|meshes`'s own `provider.policy` field
            // (`docs/DESIGN-provider-routing-policies.md` in the main repo) — this pack adds
            // no new routing logic of its own, it only exposes a UI for logic the platform
            // already has.
            id: "VideoRouter.ProviderPolicy",
            name: "Provider Selection Strategy",
            category: ["VideoRouter", "Routing", "Provider Strategy"],
            type: "combo",
            options: [
                { value: "lowest_cost", text: "Lowest cost" },
                { value: "fast_finish", text: "Fastest finish (lowest measured latency)" },
                { value: "most_reliable", text: "Most reliable (highest measured success rate)" },
                { value: "fast_start", text: "Fastest start (lowest measured queue time)" },
            ],
            // "Lowest cost" is also the platform's own unconditional default whenever no
            // policy is sent at all (`docs/DESIGN-provider-routing-policies.md` §5) — making
            // it the explicit default here too means this widget never shows an ambiguous
            // "platform default" placeholder, just the real behavior a fresh install gets.
            defaultValue: "lowest_cost",
            tooltip: "Which host videorouter.sh picks among the confirmed-identical hosts "
                    + "for a model — same 4 strategies as ComfyUI's own local hardware "
                    + "routing, applied to the hosted providers this pack relays to instead. "
                    + "Requires restarting ComfyUI to take effect (read once at pack load).",
        },
    ],
});
