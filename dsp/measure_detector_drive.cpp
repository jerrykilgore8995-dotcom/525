#include "DetectorDrive.h"

#include <iomanip>
#include <iostream>

int main()
{
    double position;
    int ceiling, limit;
    std::cout << std::setprecision(17);
    while (std::cin >> position >> ceiling >> limit)
        std::cout << vintage525::detectorDrive(position, ceiling, limit != 0) << '\n';
    return std::cin.eof() ? 0 : 1;
}
