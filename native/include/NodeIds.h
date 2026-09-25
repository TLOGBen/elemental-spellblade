#pragma once
// Addresses of skill-tree nodes as the ESP lays them out (build_v03.py, ESSBTrees.psc):
//   tree 0..12 (0-10 elements fire..astral, 11 no form, 12 common), route 0 sustain / 1 opening / 2 closing,
//   tier 0 novice .. 4 legend; a main line is a 15-rank perk chain, a branch is one perk (index 0..3).
// The concrete nodes N2 reads are generated into ManifestData.h by build/fix19_native.py, which checks
// each slot's name / text against the ESP's node table so a slot that holds a different node fails the build.
#include <cstdint>

namespace essb {

struct NodeId {
    int tree;
    int route;
    int tier;
};

struct BranchId {
    int tree;
    int route;
    int tier;
    int index;
};

inline constexpr NodeId kNoNode{ -1, -1, -1 };

constexpr bool IsNode(const NodeId& id) noexcept
{
    return id.tree >= 0;
}

}  // namespace essb
