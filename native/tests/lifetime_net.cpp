// Round 27d (0.27.3): the negative control of native/build.py's lifetime net. It MUST draw a dangling warning under
// clang-cl -Werror=dangling-gsl (a view bound to a temporary that dies at the end of the line) -- if it compiles cleanly,
// the net is not armed and the build fails. Never built into the DLL or a test.
#include <string>
#include <string_view>

int main()
{
    std::string_view name = std::string("a temporary");
    return static_cast<int>(name.size());
}
