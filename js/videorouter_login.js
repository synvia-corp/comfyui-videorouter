// Redirects ComfyUI's OWN native "Sign In" trigger to videorouter.sh's real login/signup
// page instead of showing the built-in comfy.org account modal — per explicit product
// decision: don't collect a password inside a third-party plugin's own UI (a real trust/
// phishing-pattern concern even though this is our own real backend on the other end);
// send the user to the real, trusted `videorouter.sh` domain to log in instead, same as
// any legitimate "Sign in" redirect would.
//
// Mechanism confirmed against ComfyUI_frontend's real source, 2026-09-14
// (`src/composables/useCoreCommands.ts` registers `Comfy.User.OpenSignInDialog`,
// `src/stores/commandStore.ts`'s `registerCommand` only warns — never rejects — on a
// duplicate id, then unconditionally overwrites it): re-registering a command with that
// SAME id, loaded after core, replaces core's handler. This intercepts the topbar/user-menu
// "Sign In" button (`src/components/topbar/LoginButton.vue` calls
// `commandStore.execute('Comfy.User.OpenSignInDialog')`).
//
// KNOWN GAP, not solved here: the separate dialog ComfyUI shows when running an official
// Partner API node with no credentials configured (`ApiNodesSignInContent.vue`) calls
// `dialogService.showSignInDialog()` directly, not through this command — its own internal
// "Sign In" button is NOT intercepted by this override and may still show the real
// comfy.org modal. No documented/stable hook to intercept that path was found; fixing it
// would mean a DOM MutationObserver hack against an unstable internal component, not
// something built here.
import { app } from "../../scripts/app.js";

app.registerExtension({
    name: "videorouter.login",
    commands: [
        {
            id: "Comfy.User.OpenSignInDialog",
            label: "Log In to VideoRouter",
            function: () => {
                window.open("https://videorouter.sh/login", "_blank");
            },
        },
    ],
});
