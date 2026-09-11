package dev.wha.app.ui.theme

import androidx.compose.material3.Typography
import androidx.compose.ui.unit.sp

// The system font at Material 3 defaults, with bodyLarge line height raised for reading.
val WhaTypography = Typography().copy(
    bodyLarge = Typography().bodyLarge.copy(lineHeight = 26.sp),
)
