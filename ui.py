"""Shared UI helpers: mobile-first page setup and styling."""

import streamlit as st

PAGE_ICON = "🏋️"

# One stylesheet for every page.  The app is used on a phone at the gym, so the
# defaults that matter are: full-width tap targets at least 48px tall, no iOS
# zoom-on-focus, and columns that wrap instead of squeezing into slivers.
MOBILE_CSS = """
<style>
  /* Tighter chrome so the first exercise is visible without scrolling. */
  .block-container {
      padding-top: 2.2rem;
      padding-bottom: 4rem;
      max-width: 720px;
  }
  @media (max-width: 640px) {
      .block-container {
          padding-left: 0.8rem;
          padding-right: 0.8rem;
      }
  }

  /* Thumb-sized buttons. Streamlit shrink-wraps the wrapper divs, so the
     wrappers have to be stretched before the button can fill the row. */
  [data-testid="stElementContainer"]:has(> [data-testid="stButton"]),
  [data-testid="stElementContainer"]:has(> [data-testid="stDownloadButton"]),
  [data-testid="stButton"],
  [data-testid="stDownloadButton"] {
      width: 100% !important;
  }
  [data-testid="stButton"] button,
  [data-testid="stDownloadButton"] button,
  [data-testid="stFormSubmitButton"] button {
      width: 100%;
      min-height: 3rem;
      border-radius: 12px;
      font-size: 1rem;
      font-weight: 600;
      -webkit-tap-highlight-color: transparent;
  }
  [data-testid="stButton"] button:disabled {
      opacity: 0.75;
  }

  /* Day picker chips: tall enough to hit, spread across the row. */
  [data-testid="stButtonGroup"],
  [data-testid="stButtonGroup"] > div {
      width: 100%;
  }
  [data-testid="stButtonGroup"] > div {
      display: flex;
  }
  [data-testid="stButtonGroup"] button {
      min-height: 2.6rem;
      flex: 1 1 auto;
  }

  /* iOS zooms the viewport when a focused input is under 16px. */
  input, select, textarea {
      font-size: 16px !important;
  }

  /* Streamlit keeps columns side by side at any width; let them wrap on
     phones so a 3-column row becomes two readable rows. */
  @media (max-width: 640px) {
      [data-testid="stHorizontalBlock"] {
          flex-wrap: wrap;
          gap: 0.4rem;
      }
      [data-testid="stColumn"] {
          min-width: 30% !important;
      }
      h1 { font-size: 1.6rem !important; }
      h2 { font-size: 1.25rem !important; }
  }

  /* Exercise cards: rounded, and tight enough to fit a few per screen. */
  [data-testid="stVerticalBlockBorderWrapper"] {
      border-radius: 14px;
  }
  [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] {
      gap: 0.45rem;
  }

  /* Local deployment: no cloud deploy button, no "hosted with Streamlit". */
  [data-testid="stToolbar"] { display: none; }
  footer { visibility: hidden; }
</style>
"""


def setup_page(title, subtitle=None):
    """Apply page config + shared styling.  Call once at the top of a page."""
    st.set_page_config(
        page_title=title,
        page_icon=PAGE_ICON,
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    st.markdown(MOBILE_CSS, unsafe_allow_html=True)
    st.title(title)
    if subtitle:
        st.caption(subtitle)


def pick_one(label, options, key, default=None):
    """Horizontal single-select that stays tappable on a phone.

    Uses ``st.segmented_control`` where available and falls back to a
    horizontal radio on older Streamlit versions.
    """
    if not options:
        return None
    default = default if default in options else options[0]

    if hasattr(st, "segmented_control"):
        choice = st.segmented_control(
            label, options, default=default, key=key, label_visibility="collapsed"
        )
        # segmented_control allows deselecting; treat that as "keep current".
        return choice or default

    return st.radio(
        label, options, index=options.index(default), key=key,
        horizontal=True, label_visibility="collapsed",
    )


def format_weight(weight):
    """`45.0` reads better as `45`; bodyweight moves show as BW."""
    if weight is None:
        return "BW"
    if float(weight) == 0:
        return "BW"
    if float(weight).is_integer():
        return f"{int(weight)} lbs"
    return f"{weight:g} lbs"


def rerun():
    """st.rerun landed in 1.27; keep working on older builds."""
    if hasattr(st, "rerun"):
        st.rerun()
    else:  # pragma: no cover - legacy Streamlit
        st.experimental_rerun()
