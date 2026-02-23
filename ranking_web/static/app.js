document.addEventListener("DOMContentLoaded", () => {
    const filterInput = document.querySelector("[data-table-filter]");
    const table = document.getElementById("scoreTable");

    if (filterInput && table) {
        const rows = Array.from(table.querySelectorAll("tbody tr"));
        filterInput.addEventListener("input", () => {
            const q = filterInput.value.trim().toLowerCase();
            rows.forEach((row) => {
                const text = row.textContent.toLowerCase();
                row.style.display = q && !text.includes(q) ? "none" : "";
            });
        });
    }

    const flashList = document.querySelectorAll(".flash");
    if (flashList.length) {
        setTimeout(() => {
            flashList.forEach((el) => {
                el.style.transition = "opacity 0.6s ease";
                el.style.opacity = "0.08";
            });
        }, 5000);
    }

    const modeSelect = document.querySelector("select[name='trade_date_mode']");
    const fixedInput = document.querySelector("input[name='fixed_trade_date']");
    if (modeSelect && fixedInput) {
        const sync = () => {
            const useFixed = modeSelect.value === "fixed";
            fixedInput.disabled = !useFixed;
            if (!useFixed) {
                fixedInput.value = "";
            }
        };
        modeSelect.addEventListener("change", sync);
        sync();
    }
});
