# Changelog

## Unreleased

- The display is called **Ulanzi TC002 (AWTRIX NG)**: the device first, as
  the device model already was.
- An empty **App name** saves, and means `FiestaBoard`: FiestaBoard's settings
  form does not fill in a setting's default, and the field failed its pattern.
- A page that leaves the third row empty is drawn as two rows in the middle
  of the panel, each with its gap, rather than at the top.
- README: pictures of the clock and of the setup, and how to make pages for
  the clock.

## 0.1.0

- First version: FiestaBoard pages on a Ulanzi TC002 running AWTRIX NG, as a
  pushed app in the clock's rotation, 3 rows × 13 characters in the 3×5 font.
- LED transitions streamed at five frames a second; fade through black or blend.
- Show on change, display time, app name, Basic Auth.
- Find my clock, Test connection, and the page sent again after the clock restarts.
