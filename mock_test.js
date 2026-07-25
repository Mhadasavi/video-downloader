// Mock global browser objects
global.window = {
    getComputedStyle: () => ({
        getPropertyValue: () => " #ffffff "
    }),
    innerWidth: 1200,
    addEventListener: () => {}
};
global.document = {
    getElementById: (id) => {
        // Return a mock element with standard methods/properties
        return {
            id: id,
            style: {},
            classList: {
                add: () => {},
                remove: () => {},
                includes: () => false
            },
            addEventListener: () => {},
            appendChild: () => {},
            value: "",
            textContent: "",
            innerHTML: "",
            disabled: false,
            checked: false,
            dispatchEvent: () => {}
        };
    },
    documentElement: {},
    createElement: () => ({
        style: {},
        classList: { add: () => {}, remove: () => {} },
        addEventListener: () => {}
    })
};
global.EventSource = class {
    constructor() {}
    addEventListener() {}
};

// Now require/execute the check_script.js
require('./check_script.js');
console.log("No runtime issues during initialization!");
