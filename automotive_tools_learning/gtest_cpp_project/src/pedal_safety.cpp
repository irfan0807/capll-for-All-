#include "pedal_safety.h"

PedalResult PedalSafetyFilter::Process(float raw_value) {
    // Reject NaN, Inf, and out-of-range values
    if (std::isnan(raw_value) ||
        std::isinf(raw_value) ||
        raw_value < MIN_VALID  ||
        raw_value > MAX_VALID) {
        return { InputStatus::INVALID, 0.0f };
    }
    return { InputStatus::VALID, raw_value };
}
