#include <node_api.h>
#include <dlfcn.h>
#include <string>

struct Task { napi_async_work work; napi_ref callback; std::string library, socket; bool preflight; void *handle = nullptr; };
static void execute(napi_env, void *data) {
  auto *task = static_cast<Task *>(data);
  task->handle = dlopen(task->library.c_str(), RTLD_NOW | RTLD_LOCAL);
  if (!task->handle) return;
  auto entry = reinterpret_cast<void (*)(const char *, int)>(dlsym(task->handle, "glim_hands_socket"));
  if (entry) entry(task->socket.c_str(), task->preflight ? 1 : 0);
}
static void complete(napi_env env, napi_status, void *data) {
  auto *task = static_cast<Task *>(data);
  if (task->handle) dlclose(task->handle);
  napi_value callback, global, ignored;
  napi_get_reference_value(env, task->callback, &callback);
  napi_get_global(env, &global);
  napi_call_function(env, global, callback, 0, nullptr, &ignored);
  napi_delete_reference(env, task->callback);
  napi_delete_async_work(env, task->work); delete task;
}
static bool string_arg(napi_env env, napi_value value, std::string &out) {
  size_t len = 0;
  if (napi_get_value_string_utf8(env, value, nullptr, 0, &len) != napi_ok || len == 0 || len > 4096) return false;
  out.resize(len + 1); napi_get_value_string_utf8(env, value, out.data(), out.size(), &len); out.resize(len); return true;
}
static napi_value start(napi_env env, napi_callback_info info) {
  size_t argc = 4; napi_value argv[4];
  napi_get_cb_info(env, info, &argc, argv, nullptr, nullptr);
  auto *task = new Task{};
  napi_valuetype type;
  if (argc != 4 || !string_arg(env, argv[0], task->library) || !string_arg(env, argv[1], task->socket) ||
      napi_typeof(env, argv[3], &type) != napi_ok || type != napi_function ||
      napi_get_value_bool(env, argv[2], &task->preflight) != napi_ok) {
    delete task; napi_throw_error(env, nullptr, "native library, socket and preflight required"); return nullptr;
  }
  napi_create_reference(env, argv[3], 1, &task->callback);
  napi_value name; napi_create_string_utf8(env, "Glim hands", NAPI_AUTO_LENGTH, &name);
  napi_create_async_work(env, nullptr, name, execute, complete, task, &task->work);
  napi_queue_async_work(env, task->work);
  napi_value result; napi_get_undefined(env, &result); return result;
}
NAPI_MODULE(NODE_GYP_MODULE_NAME, [](napi_env env, napi_value exports) {
  napi_value fn; napi_create_function(env, "start", NAPI_AUTO_LENGTH, start, nullptr, &fn);
  napi_set_named_property(env, exports, "start", fn); return exports;
})
