#pragma once
// Round 27b (review A N4): every lock of ours counts itself on the thread that holds it, and so do the engine lock scopes
// we enter ourselves (the alias list's read lock in Plugin.cpp QuestObjectAlias). SehFilter never swallows an access
// violation while the count is above 0: an abandoned lock would turn the fault into a hang (the swallowed exception
// skips the guard's unlock under /EHsc). Pure; native/tests/runtime_test.cpp checks the count.
#include <mutex>

namespace essb::lk {

// How many of our locks (and known engine lock scopes) this thread holds right now.
inline thread_local int t_held = 0;

inline int Held() noexcept
{
    return t_held;
}

// std::mutex that counts itself (BasicLockable + try_lock: std::lock_guard, std::unique_lock work with it).
class Mutex
{
public:
    void lock()
    {
        m_.lock();
        ++t_held;
    }
    bool try_lock()
    {
        if (m_.try_lock()) {
            ++t_held;
            return true;
        }
        return false;
    }
    void unlock()
    {
        --t_held;
        m_.unlock();
    }

private:
    std::mutex m_;
};

// An engine lock we take ourselves, in a frame that may hold no C++ objects (SEH-only): count it by hand.
inline void EnterEngineLock() noexcept
{
    ++t_held;
}
inline void LeaveEngineLock() noexcept
{
    --t_held;
}

}  // namespace essb::lk
