// Load our fixed native recorder library inside the Premonition executable.
#include <node_api.h>
#include <dlfcn.h>
#include <string>
static napi_value run(napi_env env, napi_callback_info info) {
  size_t argc = 1; napi_value argv[1];
  napi_get_cb_info(env, info, &argc, argv, nullptr, nullptr);
  char role[32] = {}; size_t size;
  if (argc != 1 || napi_get_value_string_utf8(env, argv[0], role, sizeof(role), &size) != napi_ok) {
    napi_throw_error(env, nullptr, "Native role required"); return nullptr;
  }
  const bool canary = std::string(role) == "canary";
  if (!canary && std::string(role) != "capture") { napi_throw_error(env, nullptr, "Unknown native role"); return nullptr; }
  Dl_info location;
  if (!dladdr((void*)&run, &location)) { napi_throw_error(env, nullptr, "Cannot locate native bridge"); return nullptr; }
  std::string own(location.dli_fname);
  std::string library = own.substr(0, own.find_last_of('/') + 1) + (canary ? "canary.dylib" : "capture.dylib");
  void* handle = dlopen(library.c_str(), RTLD_NOW | RTLD_LOCAL);
  if (!handle) { napi_throw_error(env, nullptr, dlerror()); return nullptr; }
  auto entry = (void(*)())dlsym(handle, canary ? "glim_canary_main" : "glim_capture_main");
  if (!entry) { napi_throw_error(env, nullptr, dlerror()); return nullptr; }
  entry();
  napi_value result; napi_get_undefined(env, &result); return result;
}
static napi_value init(napi_env env, napi_value exports) {
  napi_value fn; napi_create_function(env, "run", NAPI_AUTO_LENGTH, run, nullptr, &fn);
  napi_set_named_property(env, exports, "run", fn); return exports;
}
NAPI_MODULE(NODE_GYP_MODULE_NAME, init)
