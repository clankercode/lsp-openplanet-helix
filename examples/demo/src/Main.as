// Original minimal Openplanet demo. The marked error is intentional.
void Main() {
    int laps = 3;
    print("Hello from Helix!");
    laps = "three"; // LSP: assigning string to int
}

void RenderMenu() {
    if (UI::MenuItem("Helix demo")) {
        print("Openplanet language tools are connected.");
    }
}
