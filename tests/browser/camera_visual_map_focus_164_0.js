async (page) => {
    // Real map bridge; no mocked handlers or map routes.
    await page.locator('[data-camera-location]').click();
    await page.waitForFunction(() => {
        const frame = document.querySelector('.map-window iframe');
        if (typeof frame?.contentWindow.focusBlacknetMapSignal !== 'function'
            || !frame.contentWindow.blacknetCoordinateFocusLayer) return false;
        const center = frame.contentWindow.eval('map.getCenter()');
        return Math.abs(center.lat - 48.864173348628704) < .0001
            && Math.abs(center.lng - 2.330499567661377) < .0001;
    }, {}, {timeout:30000});
    const position = await page.locator('.map-window iframe').evaluate(frame => ({
        marker: frame.contentWindow.blacknetCoordinateFocusLayer.getLatLng(),
        center: frame.contentWindow.eval('map.getCenter()')
    }));
    const matches = point => Math.abs(point.lat - 48.864173348628704) < .0001
        && Math.abs(point.lng - 2.330499567661377) < .0001;
    if (!matches(position.marker) || !matches(position.center)) throw new Error('Incorrect camera map focus');
    await page.screenshot({path:'artifacts/cvn-164-camera-map-focus.png'});
    await page.locator('.map-window .close-btn').click();
    return {mapFocus:'PASS', ...position};
}
