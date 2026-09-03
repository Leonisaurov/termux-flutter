solutions = [
  {
    "custom_deps": {
      # Flutter 3.47.2's Skia pin. Keep this explicit because the CI host
      # must build the Termux/Bionic variant from the complete Skia checkout.
      "engine/src/flutter/third_party/skia": "https://skia.googlesource.com/skia.git@8df24be66531469e576a806749a0202ae26b8d08",
    },
    "deps_file": "DEPS",
    "managed": False,
    "name": ".",
    "safesync_url": "",
    "url": "https://github.com/flutter/flutter.git",
    "custom_vars": {
      "download_emsdk": False,
      "download_dart_sdk": False,
      "download_linux_deps": False,
      "download_fuchsia_deps": False,
      "download_android_deps": True,
      "use_rbe": False,
    }
  }
]
