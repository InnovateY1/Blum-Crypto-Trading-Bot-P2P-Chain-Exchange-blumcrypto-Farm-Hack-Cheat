function shuffle(array, excludeIndices) {
    let filteredArray = array.filter((_, index) => !excludeIndices.includes(index));

    for (let i = filteredArray.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [filteredArray[i], filteredArray[j]] = [filteredArray[j], filteredArray[i]];
    }

    let resultArray = [];
    let shuffleIndex = 0;

    for (let i = 0; i < array.length; i++) {
        if (excludeIndices.includes(i)) {
            resultArray.push(array[i]);
        } else {
            resultArray.push(filteredArray[shuffleIndex]);
            shuffleIndex++;
        }
    }
    return resultArray;
}

// Function to handle the shuffle logic
function performShuffle() {
    // فرض می‌کنیم این تابع به طور غیر همزمان کاری انجام می‌دهد
    const getCountSuccess = document.querySelectorAll('div.border-emerald-400, div.border-rose-400, div.border-blue-400');
    const count = getCountSuccess.length;
    if (count < 12) {
        // Collect all elements with the data-index attribute
        const elements = document.querySelectorAll('[data-index]');
        const values = Array.from(elements).map(el => el.querySelector('.truncate').innerText);

        // Determine which indices should be excluded from the shuffle
        const excludeIndices = Array.from(elements).map((el, index) =>
            el.classList.contains('border-emerald-400') && el.classList.contains('text-emerald-400') ? index : -1
        ).filter(index => index !== -1);

        // Shuffle the values, excluding the specified indices
        const shuffledValues = shuffle(values, excludeIndices);

        // Assign the shuffled values back to the elements
        shuffledValues.forEach((value, index) => {
            elements[index].querySelector('.truncate').innerText = value;
        });
    }
}

function start() {
    const emeraldValues = [];
    const emeraldClasses = [];
    const otherValues = [];
    const otherClasses = [];

    if (emeraldValues.length > 0 || emeraldClasses.length > 0 || otherValues.length > 0 || otherClasses.length > 0) {
        // Collect all elements with the data-index attribute
        const elements = document.querySelectorAll('[data-index]');

        // Shuffle the otherValues while keeping emerald elements in place
        function shuffleArray(array) {
            for (let i = array.length - 1; i > 0; i--) {
                const j = Math.floor(Math.random() * (i + 1));
                [array[i], array[j]] = [array[j], array[i]];
            }
        }

        shuffleArray(otherValues);

        // Update elements with shuffled values and restore classes
        elements.forEach(el => {
            const index = el.dataset.index;
            const emeraldElement = emeraldClasses.find(e => e.index === index);
            const otherElement = otherClasses.find(e => e.index === index);

            if (emeraldElement) {
                el.querySelector('.truncate').innerText = emeraldElement.text;
                el.className = emeraldElement.classes;
            } else if (otherElement) {
                el.querySelector('.truncate').innerText = otherValues.shift();
                el.className = otherElement.classes;
            }
        });
    }

    performShuffle();
}

function executeWithDelay(i) {

    if(i == 1){
        performShuffle();
    }

    if (i >= 3) {
        return;
    }
    setTimeout(function () {
        console.log('loop....')
        start();
        executeWithDelay(i + 1);
    }, 5000);
}

executeWithDelay(1); 