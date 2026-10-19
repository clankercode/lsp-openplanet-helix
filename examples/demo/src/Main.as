// Original minimal Openplanet demo. The marked error is intentional.
void Main() {
    int _laps = 3;
    print("Hello from Helix!");
    missing_counter += 1; // intentional unresolved identifier
}

void RenderMenu() {
    if (UI::MenuItem("Helix demo")) {
        print("Openplanet language tools are connected.");
    }
}
