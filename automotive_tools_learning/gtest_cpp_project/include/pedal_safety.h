#pragma once
#include <cstdint>
#include <limits>
#include <cmath>

enum class InputStatus : uint8_t { VALID = 0, INVALID = 1 };

struct PedalResult {
    InputStatus status;
    float       safe_value;
};

// ─────────────────────────────────────────────────────────────
//  PedalSafetyFilter  –  validates accelerator pedal % (0..100)
// ─────────────────────────────────────────────────────────────
class PedalSafetyFilter {
public:
    static constexpr float MIN_VALID = 0.0f;
    static constexpr float MAX_VALID = 100.0f;

    PedalResult Process(float raw_value);
};
