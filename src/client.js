"use strict";

function checkStatus(res) {
  if (res.status != 200) {
    throw new Error(`Bad status ${res.status} ${res.statusText}`);
  }
}

function getRatelimitState(res) {
  const remaining = parseInt(res.headers.get("requests-remaining") || "", 10);
  const resetAfter = parseInt(res.headers.get("requests-reset") || "", 10);

  if (isNaN(remaining) || isNaN(resetAfter)) {
    throw new Error("Invalid ratelimit response from API");
  }

  return {
    remaining,
    resetAt: Date.now() + resetAfter * 1000,
  };
}

async function performApiRequest(state, path) {
  const res = await fetch(`/api/${encodeURIComponent(path)}`, {
    headers: {
      authorization: `Bearer ${state.token}`,
    },
  });
  checkStatus(res);
  return res;
}

async function sleep(ms) {
  return new Promise((res) => setTimeout(() => res, ms));
}

async function obeyRatelimit(limit) {
  const now = Date.now();
  console.log({
    now,
    limit,
  });

  if (limit.remaining == 0 && now < limit.resetAt) {
    const sleepTime = limit.resetAt - now;
    console.log(`Sleeping for ${sleepTime / 1000} sec`);
    await sleep(sleepTime);
    console.log("Sleep done");
  }
}

const LOCALSTORAGE_STATE_KEY = "state";

function genState(token) {
  return {
    token,
    ratelimit: {
      remaining: 0,
      resetAt: 0,
    },
  };
}

function getState() {
  const stateText = localStorage.getItem(LOCALSTORAGE_STATE_KEY) || "{}";
  const data = JSON.parse(stateText);

  if (!data || !data.token || !data.ratelimit) {
    return null;
  }

  return data;
}

function setState(state) {
  localStorage.setItem(LOCALSTORAGE_STATE_KEY, JSON.stringify(state));
}

async function makeRequest(state, path) {
  await obeyRatelimit(state.ratelimit);
  const res = await performApiRequest(state, path);
  return [{ ...state, ratelimit: getRatelimitState(res) }, res];
}
