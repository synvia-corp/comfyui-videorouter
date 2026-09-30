# comfyui-videorouter

ComfyUI custom nodes for [videorouter.sh](https://videorouter.sh) — call our hosted
image/video/3D/audio generation API (100+ models, price/failover routing across providers)
from inside a ComfyUI graph, billed to your existing `llmr_sk_...` credits.

Works identically on ComfyUI Desktop and manual/portable installs — same `custom_nodes/`
layout, no desktop-specific fork.

## What this does

Two independent pieces, both enabled just by installing this pack:

1. **Its own nodes** (`VideoRouter Image Generate` / `Image Edit` / `Model Picker`) — text-to-image
   and image-to-image via videorouter.sh's `/v1/images`.
2. **A Partner Node relay** — redirects ComfyUI's own **official** Partner API Nodes (Kling,
   MiniMax, BFL, Veo, and 20+ more — the ones that normally bill through a comfy.org account)
   to bill through your videorouter.sh account instead. No changes to those nodes, no
   comfy.org login required. Every other official Partner Node this relay doesn't specifically
   handle is untouched — transparently relayed to the real `api.comfy.org` — so installing this
   pack never breaks a node it doesn't cover.

Every relayed request is translated into a call to videorouter.sh's own unified
`/v1/images`/`/v1/videos`/`/v1/meshes`/`/v1/audio/*` endpoints (never a separate
direct-to-provider path), so pricing, multi-host failover, and sandbox behavior all stay
defined in exactly one place — this pack duplicates none of it.

## Install

Via [ComfyUI Manager](https://github.com/Comfy-Org/ComfyUI-Manager): search "VideoRouter".

Manually: clone this repo into your ComfyUI install's `custom_nodes/` directory and restart
ComfyUI.

## Auth

Set your API key once — every node picks it up automatically. Checked in this order:

1. **ComfyUI Settings → VideoRouter → Auth → API Key** (recommended). Saved server-side by
   ComfyUI itself, never into a shared `workflow.json`.
2. A node's own `api_key` widget — a per-node override. Avoid this for anything you'll
   share: ComfyUI has no masked/password input type, and a widget value gets saved into
   `workflow.json` — a live key in a workflow file pasted into a forum/Discord is a real
   credential leak.

Get a key at [videorouter.sh/keys](https://videorouter.sh/keys).

## Provider selection strategy

**ComfyUI Settings → VideoRouter → Routing → Provider Selection Strategy** picks which host
videorouter.sh routes a relayed Partner Node request to, among the confirmed-identical hosts
for that model — the same 4 strategies ComfyUI itself uses for local hardware routing,
applied here to the hosted providers instead:

- **Platform default (cheapest first)** — no preference set, the platform's own default.
- **Lowest cost**
- **Fastest finish** — lowest measured end-to-end generation latency.
- **Most reliable** — highest measured success rate.
- **Fastest start** — lowest measured queue time before generation begins.

This is a single global setting, not a per-node control — none of the official Partner Node
schemas this pack relays have a host-selection input of their own to attach one to. Takes
effect on ComfyUI's next restart (read once at pack load, same as the API key).

**Price badge**: for the 3 nodes this pack has live-verified most heavily this session —
`Kling Text to Video`, `MiniMax Hailuo 03 Text to Video` ("MiniMax H3" option), and
`Google Veo 3 Video Generation` — the price badge shown in the node graph is patched at
install time to compute this platform's own real price instead of comfy.org's hardcoded
credit estimate (see `price_patch.py`; no frontend fork required for the *number* itself to
be correct). By default it's still shown in comfy.org's own "credits" unit, since that
conversion is baked into the stock ComfyUI frontend — installing the optional
[videorouter-fork ComfyUI frontend](https://github.com/Franklin-Yao/comfyui_frontend_fork)
(built separately, launched with `--front-end-root`) instead makes these 3 badges show a
real `$` amount directly. Every OTHER relayed node (23+ providers) still shows comfy.org's
own original estimate — this pack has no way to rewrite another node's schema at all unless
explicitly patched like the 3 above. What you're actually billed always follows your
videorouter.sh account's real pricing and the routing strategy above, never the number
displayed in the node.

## Nodes

| Node | Maps to |
|---|---|
| VideoRouter Image Generate | `POST /v1/images` (text-to-image) |
| VideoRouter Image Edit | `POST /v1/images` (image-to-image) |
| VideoRouter Model Picker | live combo widget over `GET /v1/images/models` |

## Partner Node relay coverage

Only the request shapes listed below have a confirmed price and are billed through this
relay — anything else on a covered provider prefix is rejected with a clear error rather
than silently guessed at, and any *other* provider's official node is passed straight
through to comfy.org, unaffected.

| Provider | Coverage |
|---|---|
| **Kling** | Text-to-video (substituted to `kling-v2-6` Standard) + "Kling 3.0 Turbo" (exact-match `pika/kling-3.0-turbo`) |
| **MiniMax H3** | Text-to-video (`MiniMax H3` option only — H3 Max/Max Turbo not yet relayed) |
| **BFL / FLUX** | `flux-pro-1.1-ultra`, `flux-kontext-pro`, `flux-kontext-max` (flat, size-independent pricing only) |
| **OpenAI (GPT Image)** | `images/generations` — all 5 GPT Image models |
| **Veo** | Text/image-to-video, `veo-3.1`/`veo-3.1-fast`/`veo-3.1-lite` (substituted onto this platform's multi-host Veo rows — gets automatic price/failover across hosts for free) |
| **Luma** | Text-to-video (substituted onto `luma-ray-3.2`) |
| **Runway** | Aleph 2 video-to-video edit only |
| **LTX** | Text/image-to-video (`ltx-2.5-fast`/`-pro`) |
| **OpenRouter** | Image generation only |
| **Meta** | Muse Image generation |
| **xAI / Grok** | Text/image-to-video + image generation |
| **Qwen** | Text-to-image |
| **Wan** | `wan-2.7`/`wan-3.0`/`wan-3.0-prime`/`happy-horse-1.1` |
| **Ideogram** | `IdeogramV4` (DEFAULT/QUALITY speed only) |
| **Recraft** | `RecraftTextToImageNode` (realistic style only) |
| **PixVerse** | `PixverseV6TextToVideoNode` |
| **Vidu** | `Vidu3TextToVideoNode` |
| **Tripo** | Text/image-to-3D (substituted onto the confirmed P2 checkpoint regardless of version picked) |
| **Hunyuan3D** | Text/image-to-3D (substituted onto a confirmed hosted checkpoint) |
| **Rodin** | Gen-2.5 image-to-3D |
| **Topaz** | Image upscale — "Wonder 3.5"/"Bloom 2" only |
| **WaveSpeed** | SeedVR2 image + video upscale (substituted onto a confirmed host; "Ultimate" not yet priced anywhere) |
| **Bria** | Background removal |
| **HeyGen** | Talking-photo avatar (bring-your-own-audio mode only) |
| **Meshy** | Text/Image/Multi-Image-to-Model (draft-quality only — the other 5 Meshy nodes operate on a previously-created task and aren't relayed) |
| **ElevenLabs** | Text-to-Speech + Speech-to-Text (Instant Voice Cloning and the other 4 nodes aren't relayed yet) |

Where a node's real requested checkpoint has no confirmed direct price, the relay
**substitutes** the closest confirmed one rather than rejecting outright (kept explicit,
never silent) — you get a real generation, just not always the exact tier/version picked in
the node's dropdown.

## Known gaps

- Every provider above has sibling/legacy nodes that aren't relayed yet (different
  endpoints or price shapes not yet confirmed) — an unrelayed node on a covered prefix
  fails with a clear error, not a silent wrong bill.
- ElevenLabs Instant Voice Cloning, Audio Isolation, Sound Effects, Speech-to-Speech, and
  Text-to-Dialogue aren't relayed.
- No first-last-frame Veo support.
- Providers not listed at all above (Anthropic, Sora, Comfy Cloud, and anything without a
  hosted price on videorouter.sh) are transparently passed through to the real comfy.org,
  unaffected by installing this pack.

## Security

Never let your API key land in a shareable `workflow.json` — workflow files get pasted into
Discord/Civitai routinely, and a leaked `llmr_sk_...` key is a live-credits leak. Use the
Settings-panel auth path above, not a node's own `api_key` widget, for anything you plan to
share.

## License

MIT
