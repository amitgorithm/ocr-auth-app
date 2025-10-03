document.addEventListener('DOMContentLoaded', function() {
    // Get radio buttons and fieldsets
    const aadharRadio = document.getElementById('aadhar');
    const panRadio = document.getElementById('pan');
    const aadharFields = document.getElementById('aadhar_fields');
    const panFields = document.getElementById('pan_fields');

    // Get input fields inside the fieldsets
    const aadharNumberInput = document.getElementById('aadhar_number');
    const aadharPhotoInput = document.getElementById('id_photo_aadhar');
    const panNumberInput = document.getElementById('pan_number');
    const panPhotoInput = document.getElementById('id_photo_pan');

    function toggleFields() {
        if (aadharRadio.checked) {
            aadharFields.style.display = 'block';
            panFields.style.display = 'none';

            // Enable Aadhar fields and disable PAN fields
            aadharNumberInput.required = true;
            aadharPhotoInput.required = true;
            aadharPhotoInput.disabled = false;
            // The actual photo input name is 'id_photo', so we ensure it's set correctly
            aadharPhotoInput.name = 'id_photo';

            panNumberInput.required = false;
            panPhotoInput.required = false;
            panPhotoInput.disabled = true;
            panPhotoInput.name = 'id_photo_pan_disabled'; // Change name to avoid submission

        } else if (panRadio.checked) {
            aadharFields.style.display = 'none';
            panFields.style.display = 'block';

            // Disable Aadhar fields and enable PAN fields
            aadharNumberInput.required = false;
            aadharPhotoInput.required = false;
            aadharPhotoInput.disabled = true;
            aadharPhotoInput.name = 'id_photo_aadhar_disabled';

            panNumberInput.required = true;
            panPhotoInput.required = true;
            panPhotoInput.disabled = false;
            panPhotoInput.name = 'id_photo'; // Set the correct name for submission
        }
    }

    // Add event listeners to radio buttons
    aadharRadio.addEventListener('change', toggleFields);
    panRadio.addEventListener('change', toggleFields);

    // Initial call to set the correct state on page load
    toggleFields();
});