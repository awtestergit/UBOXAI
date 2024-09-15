/*
    Author: awtestergit
*/

import React, { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import AppFastAPI from "./AppFastAPI.js";

const root = createRoot(document.getElementById("root"));
root.render(
  <StrictMode>
    <AppFastAPI />
  </StrictMode>
);